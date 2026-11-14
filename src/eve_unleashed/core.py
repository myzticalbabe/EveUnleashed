"""
Eve Unleashed Core
==================
Model loading, inference result types, and framework detection.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Any, List
from pathlib import Path

# Import compatibility layer first
from eve_unleashed.compat import available_frameworks as _compat_frameworks

#: Swallows recorded when the failure ledger is unavailable (it is a stdlib-only
#: leaf, so this fallback should never fire -- if it does, the ledger is missing).

try:
    from CORE.failure_ledger import note_failure
except ImportError:                               # never break the host
    def note_failure(where: str, exc: BaseException | None = None) -> None:
        pass  # ledger missing; evidence-vs-silence tradeoff capped here

# Get framework availability from compatibility layer
_COMPAT_FRAMEWORKS = _compat_frameworks()

# Cached XPU availability check (subprocess-based to survive segfaults)
_XPU_AVAILABLE: (bool | None) = None


# PIL / image support detection
try:
    from PIL import Image
    HAS_PIL = True
except ImportError as exc:
    note_failure("core:L105", exc)
    HAS_PIL = False
    Image = None  # type: ignore

# Shared data models (single source of truth across all projects): the
# dataclasses below are the unconditional fallback truth; when shared.models
# is importable the try-import overwrites them with the canonical definitions.
# Definition-before-import order is load-bearing: the checker resolves
# downstream `from .core import ...` against the first (class) binding, so a
# missing shared.models no longer hides the fallback (verified via probe).
# Runtime semantics are unchanged in every environment: shared-absent keeps
# the fallback, shared-present overwrites with the canonical classes.
from dataclasses import dataclass, field


@dataclass
class InferenceResult:
    model_name: str = ""
    framework: str = ""
    input_shape: tuple = ()
    output_shape: tuple = ()
    latency_ms: float = 0.0
    predictions: list[Any] = field(default_factory=list)
    probabilities: (list[float] | None) = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BatchResult:
    results: list[Any] = field(default_factory=list)
    total_time_ms: float = 0.0
    avg_latency_ms: float = 0.0
    throughput_per_sec: float = 0.0


try:
    from shared.models import InferenceResult, BatchResult
except ImportError as exc:
    # Fallback: local dataclasses above stand (shared module not available)
    note_failure("core:L112", exc)

# Ensure shared is importable from the library
try:
    pass
except ImportError as exc:
    note_failure("core:L137", exc)
    _shared_path = Path(__file__).resolve().parents[4] / "workspace" / "projects"
    if str(_shared_path) not in sys.path:
        sys.path.insert(0, str(_shared_path))


class ModelLoader:
    """Load and manage ML models across frameworks."""

    @staticmethod
    def detect_frameworks() -> dict[str, bool]:
        """Detect which ML frameworks are available."""
        frameworks = {}
        # Use compatibility layer for framework detection
        for name in ["torch", "tensorflow", "sklearn", "transformers", "onnx", "gguf"]:
            frameworks[name] = _COMPAT_FRAMEWORKS.get(name, False)
        
        # VL = transformers + PIL
        frameworks["vl"] = frameworks.get("transformers", False) and HAS_PIL
        
        # GPU acceleration detection
        if frameworks.get("torch"):
            try:
                import torch
                frameworks["cuda"] = torch.cuda.is_available()
                frameworks["metal"] = torch.backends.mps.is_available()
                # Intel XPU (Arc GPU via Level Zero / SYCL)
                # Uses subprocess sandbox to survive segfaults on headless systems
                frameworks["xpu"] = _check_xpu_available()
            except Exception as exc:
                note_failure("core:L175", exc)
                frameworks["cuda"] = False
                frameworks["metal"] = False
                frameworks["xpu"] = False

        # OpenCL detection (for Intel iGPU/dGPU, AMD GPUs)
        frameworks["opencl"] = False
        if _COMPAT_FRAMEWORKS.get("pyopencl", False):
            try:
                import pyopencl
                platforms = pyopencl.get_platforms()
                frameworks["opencl"] = len(platforms) > 0
            except Exception as exc:
                note_failure("core:L187", exc)

        # Vulkan detection (cross-platform GPU compute)
        frameworks["vulkan"] = False
        if frameworks.get("torch"):
            try:
                import torch
                _vulkan = getattr(torch, "vulkan", None)
                frameworks["vulkan"] = bool(_vulkan and _vulkan.is_available())
            except Exception as exc:
                note_failure("core:L198", exc)

        return frameworks

    @staticmethod
    def load_torch(model_path: str, device: str = "cpu"):
        """Load a PyTorch model."""
        import torch

        model = torch.load(model_path, map_location=device, weights_only=False)
        model.eval()
        return model

    @staticmethod
    def load_sklearn(model_path: str):
        """Load a scikit-learn model."""
        import joblib

        return joblib.load(model_path)

    @staticmethod
    def get_model_info(model_path: str) -> dict[str, Any]:
        """Get metadata about a saved model."""
        path = Path(model_path)
        if not path.exists():
            return {"error": f"Model not found: {model_path}"}

        return {
            "path": str(path.absolute()),
            "size_bytes": path.stat().st_size,
            "framework": ModelLoader._guess_framework(path),
            "last_modified": path.stat().st_mtime,
        }

    @staticmethod
    def guess_framework(path: Path) -> str:
        """Guess the framework from file extension (public API)."""
        suffix = path.suffix.lower()
        name = path.name.lower()
        if suffix in (".pt", ".pth"):
            return "torch"
        elif suffix in (".joblib", ".pkl"):
            return "sklearn"
        elif suffix == ".onnx":
            return "onnx"
        elif suffix == ".gguf":
            return "gguf"
        elif suffix in (".h5", ".keras"):
            return "tensorflow"
        elif suffix in (".safetensors", ".bin"):
            for vl_keyword in ["llava", "blip", "clip", "vit", "detr", "yolo", "resnet"]:
                if vl_keyword in name:
                    return "vl"
            return "transformers"
        return "unknown"

    @staticmethod
    def get_gpu_info() -> dict[str, Any]:
        """Get detailed GPU hardware information."""
        info: dict[str, Any] = {
            "cuda_available": False,
            "cuda_devices": 0,
            "cuda_version": "",
            "metal_available": False,
            "xpu_available": False,
            "xpu_devices": 0,
            "opencl_available": False,
            "vulkan_available": False,
            "device_count": 0,
            "devices": [],
            "recommended_device": "cpu",
        }
        # Check if torch is available via compat layer
        if _COMPAT_FRAMEWORKS.get("torch", False):
            try:
                import torch
                info["cuda_available"] = torch.cuda.is_available()
                info["metal_available"] = torch.backends.mps.is_available()
                # Use crash-safe subprocess check — direct call can segfault
                info["xpu_available"] = _check_xpu_available()
                if info["cuda_available"]:
                    info["cuda_devices"] = torch.cuda.device_count()
                    info["cuda_version"] = torch.version.cuda or ""
                    for i in range(torch.cuda.device_count()):
                        props = torch.cuda.get_device_properties(i)
                        info["devices"].append({
                            "index": i,
                            "name": props.name,
                            "total_memory_gb": round(props.total_memory / (1024**3), 2),
                            "compute_capability": f"{props.major}.{props.minor}",
                            "backend": "cuda",
                        })
                if info["xpu_available"]:
                    info["xpu_devices"] = torch.xpu.device_count()
                    for i in range(torch.xpu.device_count()):
                        try:
                            name = torch.xpu.get_device_name(i)
                            props = torch.xpu.get_device_properties(i)
                            info["devices"].append({
                                "index": i,
                                "name": name,
                                "total_memory_gb": round(props.total_memory / (1024**3), 2),
                                "backend": "xpu",
                            })
                        except Exception as exc:
                            note_failure("core:L301", exc)
                            info["devices"].append({
                                "index": i,
                                "name": f"Intel XPU Device {i}",
                                "backend": "xpu",
                            })
                if info["metal_available"]:
                    info["devices"].append({
                        "index": 0,
                        "name": "Apple Metal (MPS)",
                        "backend": "mps",
                    })
            except ImportError as exc:
                note_failure("core:L313", exc)

        # OpenCL detection (independent of torch)
        try:
            import pyopencl
            platforms = pyopencl.get_platforms()
            if platforms:
                info["opencl_available"] = True
                for p_idx, platform in enumerate(platforms):
                    devices = platform.get_devices()
                    for d_idx, device in enumerate(devices):
                        mem = device.get_info(pyopencl.device_info.GLOBAL_MEM_SIZE)
                        info["devices"].append({
                            "index": len(info["devices"]),
                            "name": f"{platform.name} - {device.name}",
                            "total_memory_gb": round(mem / (1024**3), 2),
                            "backend": "opencl",
                        })
        except ImportError:
            pass
        except Exception as exc:
            note_failure("core:L345", exc)

        # Set recommended device
        if info["cuda_available"]:
            info["recommended_device"] = "cuda"
        elif info["xpu_available"]:
            info["recommended_device"] = "xpu"
        elif info["metal_available"]:
            info["recommended_device"] = "mps"
        elif info["opencl_available"]:
            info["recommended_device"] = "opencl"
        
        info["device_count"] = len(info["devices"])
        return info

    @staticmethod
    def get_best_device() -> str:
        """Auto-detect the best available compute device.

        Priority: CUDA > Intel XPU > Apple Metal > CPU
        Returns a device string suitable for torch.device().
        """
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            if _check_xpu_available():
                return "xpu"
            if torch.backends.mps.is_available():
                return "mps"
        except ImportError as exc:
            note_failure("core:L365", exc)
        return "cpu"

    @staticmethod
    def _guess_framework(path: Path) -> str:
        """Guess the framework from file extension (internal)."""
        return ModelLoader.guess_framework(path)


def timed_inference(fn):
    """Decorator to time inference calls."""

    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        if isinstance(result, InferenceResult):
            result.latency_ms = elapsed
        return result

    return wrapper

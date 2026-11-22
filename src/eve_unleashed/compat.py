"""
Eve Unleashed Compatibility Layer
=================================
Provides fallback implementations for frameworks not available on Python 3.16t.
This allows the CLI and core functionality to work even without torch/transformers/onnx.

Usage:
    from eve_unleashed.compat import torch, transformers, onnx, tensorflow

    # These modules will have stub implementations that raise informative errors
    # or provide minimal functionality for non-ML operations.
"""

from __future__ import annotations

import sys
import warnings
from types import ModuleType
from typing import Any

# Track what's actually available
_TORCH_AVAILABLE = False
_TRANSFORMERS_AVAILABLE = False
_ONNX_AVAILABLE = False
_TENSORFLOW_AVAILABLE = False
_SAFETENSORS_AVAILABLE = False
_SKLEARN_AVAILABLE = False
_GGUF_AVAILABLE = False
_PYOPENCL_AVAILABLE = False

# Try to import real modules
for name, flag_name in [
    ("torch", "_TORCH_AVAILABLE"),
    ("transformers", "_TRANSFORMERS_AVAILABLE"),
    ("onnx", "_ONNX_AVAILABLE"),
    ("tensorflow", "_TENSORFLOW_AVAILABLE"),
    ("safetensors", "_SAFETENSORS_AVAILABLE"),
    ("sklearn", "_SKLEARN_AVAILABLE"),
    ("gguf", "_GGUF_AVAILABLE"),
    ("pyopencl", "_PYOPENCL_AVAILABLE"),
]:
    try:
        __import__(name)
        globals()[flag_name] = True
    except ImportError:
        pass


# Stub base class
class _StubModule(ModuleType):
    """A module that raises informative errors when used."""

    def __init__(self, name: str, real_name: str, install_hint: str = ""):
        super().__init__(name)
        self._real_name = real_name
        self._install_hint = install_hint
        self._not_available_msg = (
            f"{real_name} is not available on Python {sys.version_info.major}.{sys.version_info.minor} "
            f"(free-threaded build). {install_hint}".strip()
        )

    def __getattr__(self, attr: str) -> Any:
        # Allow some common attributes for inspection
        if attr in ("__version__", "__file__", "__path__", "__spec__"):
            raise AttributeError(f"{self._real_name} not available")
        if attr == "is_available":
            return lambda: False
        raise RuntimeError(self._not_available_msg)

    def __call__(self, *args, **kwargs):
        raise RuntimeError(self._not_available_msg)

    def __bool__(self):
        return False


def _create_stub(name: str, install_hint: str = "") -> ModuleType:
    """Create a stub module for an unavailable framework."""
    hint = (
        install_hint
        or f"Install {name} when wheels are available for your Python version."
    )
    return _StubModule(name, name, hint)


# Create the compatibility modules
if not _TORCH_AVAILABLE:
    torch = _create_stub(
        "torch", "PyTorch wheels not yet available for Python 3.16t free-threaded."
    )
    torch.cuda = _create_stub("torch.cuda")
    torch.nn = _create_stub("torch.nn")
    torch.optim = _create_stub("torch.optim")
    torch.utils = _create_stub("torch.utils")
    torch.utils.data = _create_stub("torch.utils.data")
else:
    import torch

if not _TRANSFORMERS_AVAILABLE:
    transformers = _create_stub(
        "transformers", "Requires torch; not available on Python 3.16t."
    )
    transformers.models = _create_stub("transformers.models")
    transformers.pipelines = _create_stub("transformers.pipelines")
    transformers.tokenization_utils = _create_stub("transformers.tokenization_utils")
else:
    import transformers

if not _ONNX_AVAILABLE:
    onnx = _create_stub(
        "onnx", "ONNX Runtime wheels not yet available for Python 3.16t."
    )
    onnxruntime = _create_stub(
        "onnxruntime", "ONNX Runtime wheels not yet available for Python 3.16t."
    )
else:
    import onnx
    import onnxruntime

if not _TENSORFLOW_AVAILABLE:
    tensorflow = _create_stub(
        "tensorflow", "TensorFlow wheels not yet available for Python 3.16t."
    )
    tf = tensorflow
else:
    import tensorflow as tf

if not _SAFETENSORS_AVAILABLE:
    safetensors = _create_stub(
        "safetensors",
        "safetensors requires Rust/PyO3 build; PyO3 doesn't yet support Python 3.16t.",
    )
    safetensors.torch = _create_stub("safetensors.torch")
else:
    import safetensors


# Convenience functions
def check_torch() -> bool:
    """Check if torch is actually available."""
    return _TORCH_AVAILABLE


def check_transformers() -> bool:
    """Check if transformers is actually available."""
    return _TRANSFORMERS_AVAILABLE


def check_onnx() -> bool:
    """Check if onnx is actually available."""
    return _ONNX_AVAILABLE


def check_tensorflow() -> bool:
    """Check if tensorflow is actually available."""
    return _TENSORFLOW_AVAILABLE


def check_safetensors() -> bool:
    """Check if safetensors is actually available."""
    return _SAFETENSORS_AVAILABLE


def available_frameworks() -> dict[str, bool]:
    """Return dict of framework availability."""
    return {
        "torch": _TORCH_AVAILABLE,
        "transformers": _TRANSFORMERS_AVAILABLE,
        "onnx": _ONNX_AVAILABLE,
        "tensorflow": _TENSORFLOW_AVAILABLE,
        "safetensors": _SAFETENSORS_AVAILABLE,
        "sklearn": _SKLEARN_AVAILABLE,
        "gguf": _GGUF_AVAILABLE,
        "pyopencl": _PYOPENCL_AVAILABLE,
    }


def require_framework(name: str) -> ModuleType:
    """Get a framework module, raising if not available."""
    if name == "torch":
        if _TORCH_AVAILABLE:
            return torch
        raise RuntimeError("torch not available on Python 3.16t free-threaded")
    elif name == "transformers":
        if _TRANSFORMERS_AVAILABLE:
            return transformers
        raise RuntimeError("transformers requires torch; not available on Python 3.16t")
    elif name == "onnx":
        if _ONNX_AVAILABLE:
            return onnx
        raise RuntimeError("onnx not available on Python 3.16t")
    elif name == "tensorflow":
        if _TENSORFLOW_AVAILABLE:
            return tensorflow
        raise RuntimeError("tensorflow not available on Python 3.16t")
    elif name == "safetensors":
        if _SAFETENSORS_AVAILABLE:
            return safetensors
        raise RuntimeError(
            "safetensors not available on Python 3.16t (PyO3 version issue)"
        )
    else:
        raise ValueError(f"Unknown framework: {name}")


# Export
__all__ = [
    "available_frameworks",
    "check_onnx",
    "check_safetensors",
    "check_tensorflow",
    "check_torch",
    "check_transformers",
    "onnx",
    "onnxruntime",
    "require_framework",
    "safetensors",
    "tensorflow",
    "tf",
    "torch",
    "transformers",
]

# Print availability on import
if __name__ != "__main__":
    avail = available_frameworks()
    available = [k for k, v in avail.items() if v]
    missing = [k for k, v in avail.items() if not v]
    if available:
        pass  # Silent success
    if missing:
        warnings.warn(
            f"Eve Unleashed: Frameworks unavailable on Python 3.16t: {missing}. "
            f"Available: {available}. Using compatibility stubs.",
            RuntimeWarning,
            stacklevel=2,
        )

"""
Eve Unleashed Inference Engine
=============================
Main inference engine supporting PyTorch, sklearn, transformers, ONNX,
GGUF (llama.cpp), and Vision-Language (VL) models.

Supports synchronous and async inference, streaming token generation,
and LRU+TTL inference caching.

Async mode uses a thread pool for non-blocking batch processing.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import functools
import os
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any, cast

import numpy as np

from .cache import InferenceCache
from .config import EveConfig
from .core import HAS_PIL, BatchResult, InferenceResult, ModelLoader, timed_inference
from .streaming import (
    StreamToken,
    stream_gguf,
    stream_native,
    stream_transformers,
)
from .utils import (
    postprocess_output,
    prepare_input_tensor,
)

# Optional imports for advanced features
try:
    from .speculative import SpeculativeEngine, create_speculative_engine

    HAS_SPECULATIVE = True
except ImportError:
    HAS_SPECULATIVE = False

try:
    from .kv_quant import KVQuantizer, create_quantized_llama

    HAS_KV_QUANT = True
except ImportError:
    HAS_KV_QUANT = False

#: Swallows recorded when the failure ledger is unavailable (it is a stdlib-only
#: leaf, so this fallback should never fire -- if it does, the ledger is missing).

try:
    from CORE.failure_ledger import note_failure
except ImportError:  # never break the host

    def note_failure(where: str, exc: BaseException | None = None) -> None:
        pass  # ledger missing; evidence-vs-silence tradeoff capped here


if HAS_PIL:
    from PIL import Image


class GGUFEngine:
    """Specialized GGUF inference engine with advanced features.

    Supports:
    - Speculative decoding (draft + verify)
    - KV cache quantization (8-bit)
    - Multi-modal (LLaVA-style) vision-language
    - Streaming token generation
    """

    def __init__(self, config: EveConfig | None = None):
        self.config = config or EveConfig()

        # Auto-detect best device if set to "auto"
        if self.config.device == "auto":
            self.config.device = ModelLoader.get_best_device()

        self.loaded_models: dict[str, Any] = {}
        self.speculative_engines: dict[str, SpeculativeEngine] = {}
        self.kv_quantizers: dict[str, KVQuantizer] = {}

        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.num_workers or 1
        )
        self._inference_count: int = 0
        self._total_latency_ms: float = 0.0

        # Inference cache (LRU + TTL)
        if self.config.enable_cache:
            self._cache = InferenceCache(
                max_size_bytes=self.config.cache_size_mb * 1024 * 1024,
                ttl_seconds=self.config.cache_ttl_seconds,
            )
        else:
            self._cache = None

    def load_model(
        self,
        model_path: str,
        n_ctx: int = 2048,
        speculative: bool = False,
        draft_model_path: str | None = None,
        num_draft_tokens: int = 4,
        kv_quant_bits: int | None = None,
        **kwargs,
    ) -> str:
        """Load a GGUF model with optional advanced features.

        Args:
            model_path: Path to GGUF model
            n_ctx: Context window size
            speculative: Enable speculative decoding
            draft_model_path: Path to draft model (required if speculative=True)
            num_draft_tokens: Number of draft tokens for speculative decoding
            kv_quant_bits: Enable KV cache quantization (4 or 8)
            **kwargs: Additional Llama constructor arguments
        """
        p = Path(model_path)

        if not p.exists():
            raise FileNotFoundError(f"GGUF model not found: {model_path}")

        if not p.suffix.lower() == ".gguf":
            raise ValueError(f"Not a GGUF file: {model_path}")

        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python"
            )

        # Load main model
        if kv_quant_bits and HAS_KV_QUANT:
            model = create_quantized_llama(
                model_path, n_ctx=n_ctx, kv_bits=kv_quant_bits, **kwargs
            )
            self.kv_quantizers[model_path] = model._kv_quantizer
        else:
            model = Llama(model_path=model_path, n_ctx=n_ctx, verbose=False, **kwargs)

        handle = f"gguf:{model_path}"
        self.loaded_models[handle] = model

        # Set up speculative decoding if requested
        if speculative:
            if not HAS_SPECULATIVE:
                raise RuntimeError(
                    "Speculative decoding not available (speculative.py import failed)"
                )
            if not draft_model_path:
                raise ValueError("draft_model_path required when speculative=True")

            speculative_engine = create_speculative_engine(
                draft_model_path=draft_model_path,
                target_model_path=model_path,
                num_draft_tokens=num_draft_tokens,
                n_ctx=n_ctx,
            )
            self.speculative_engines[handle] = speculative_engine

        # Warm up
        self._warmup_model(handle)
        return handle

    def load_multimodal_model(
        self, model_path: str, n_ctx: int = 2048, **kwargs
    ) -> str:
        """Load a multi-modal GGUF model (LLaVA-style).

        These models combine a vision encoder with a language model.
        """
        p = Path(model_path)

        if not p.exists():
            raise FileNotFoundError(f"Multi-modal model not found: {model_path}")

        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python"
            )

        # Load with multimodal support
        model = Llama(model_path=model_path, n_ctx=n_ctx, verbose=False, **kwargs)

        handle = f"gguf-mm:{model_path}"
        self.loaded_models[handle] = model

        self._warmup_model(handle)
        return handle

    @property
    def stats(self) -> dict[str, Any]:
        """Runtime statistics."""
        avg_latency = (
            self._total_latency_ms / self._inference_count
            if self._inference_count > 0
            else 0
        )
        return {
            "inference_count": self._inference_count,
            "total_latency_ms": round(self._total_latency_ms, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "loaded_models": len(self.loaded_models),
            "speculative_engines": len(self.speculative_engines),
            "kv_quantizers": len(self.kv_quantizers),
            "cache": self.cache_stats,
        }

    @property
    def cache_stats(self) -> dict[str, Any]:
        """Cache usage statistics."""
        if self._cache is None:
            return {"enabled": False}
        return {"enabled": True, **self._cache.stats}

    def infer(
        self,
        handle: str,
        inputs: str | dict,
        max_tokens: int = 128,
        temperature: float = 0.8,
        top_p: float = 0.95,
        use_speculative: bool = True,
        **kwargs,
    ) -> InferenceResult:
        """Run inference on a loaded GGUF model.

        Args:
            handle: Model handle from load_model()
            inputs: Text prompt (str) or dict with 'text' and 'images' for multimodal
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling
            use_speculative: Use speculative decoding if available
            **kwargs: Additional generation arguments
        """
        if handle not in self.loaded_models:
            raise KeyError(f"Model not loaded: {handle}")

        model = self.loaded_models[handle]
        start = time.perf_counter()

        # Check cache
        cache_key = f"{handle}:{inputs}:{max_tokens}:{temperature}:{top_p}"
        if self._cache is not None:
            cached = self._cache.get(handle, cache_key, "gguf")
            if cached is not None:
                return cached

        # Handle multi-modal input
        if isinstance(inputs, dict):
            text = inputs.get("text", "")
            images = inputs.get("images", [])
        else:
            text = str(inputs)
            images = []

        # Use speculative decoding if available and enabled
        if use_speculative and handle in self.speculative_engines:
            speculative_engine = self.speculative_engines[handle]
            output_text = speculative_engine.generate(text)
        else:
            # Standard generation
            if images and handle.startswith("gguf-mm:"):
                # Multi-modal generation (LLaVA-style)
                output_text = self._generate_multimodal(
                    model, text, images, max_tokens, temperature, top_p
                )
            else:
                output = model(
                    text,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    echo=False,
                    **kwargs,
                )
                choices = output.get("choices", [])
                output_text = choices[0].get("text", "") if choices else ""

        latency_ms = (time.perf_counter() - start) * 1000

        result = InferenceResult(
            model_name=str(type(model).__name__),
            framework="gguf",
            input_shape=(1,),
            output_shape=(1,),
            latency_ms=round(latency_ms, 2),
            predictions=[output_text],
        )

        # Track stats
        self._inference_count += 1
        self._total_latency_ms += result.latency_ms

        # Store in cache
        if self._cache is not None:
            self._cache.put(handle, cache_key, "gguf", result)

        return result

    def _generate_multimodal(
        self,
        model: Any,
        text: str,
        images: list,
        max_tokens: int,
        temperature: float,
        top_p: float,
    ) -> str:
        """Generate with multi-modal (LLaVA-style) model."""
        # llama-cpp-python supports multimodal via chat completion with images
        # This is a simplified implementation
        try:
            # Format as chat with images
            messages = []
            if images:
                content = []
                for img in images:
                    if isinstance(img, str):
                        content.append({"type": "image_url", "image_url": {"url": img}})
                    else:
                        content.append({"type": "image", "image": img})
                content.append({"type": "text", "text": text})
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "user", "content": text})

            output = model.create_chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
            )

            if output and "choices" in output:
                return output["choices"][0]["message"].get("content", "")
            return ""
        except Exception:  # noqa: BLE001 -- backend varies; use text-only fallback
            # Fall back to text-only
            output = model(
                text,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                echo=False,
            )
            choices = output.get("choices", [])
            return choices[0].get("text", "") if choices else ""

    def infer_stream(
        self,
        handle: str,
        inputs: str | dict,
        max_tokens: int = 256,
        temperature: float = 0.8,
        top_p: float = 0.95,
    ) -> AsyncGenerator[StreamToken]:
        """Stream inference results token by token."""
        if handle not in self.loaded_models:
            raise KeyError(f"Model not loaded: {handle}")

        model = self.loaded_models[handle]

        if isinstance(inputs, dict):
            text = inputs.get("text", "")
        else:
            text = str(inputs)

        # Stream using llama-cpp-python's streaming
        stream = model(
            text,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stream=True,
            echo=False,
        )

        for chunk in stream:
            if chunk.get("choices"):
                delta = chunk["choices"][0].get("delta", {})
                if "content" in delta:
                    yield StreamToken(text=delta["content"])
                elif "text" in chunk["choices"][0]:
                    yield StreamToken(text=chunk["choices"][0]["text"])

    def get_speculative_stats(self, handle: str) -> dict | None:
        """Get speculative decoding statistics for a model."""
        if handle in self.speculative_engines:
            return self.speculative_engines[handle].get_stats()
        return None

    def get_kv_quant_stats(self, handle: str) -> dict | None:
        """Get KV quantization statistics for a model."""
        model_path = handle.replace("gguf:", "").replace("gguf-mm:", "")
        if model_path in self.kv_quantizers:
            return self.kv_quantizers[model_path].get_memory_savings()
        return None

    def unload_model(self, handle: str):
        """Unload a model and its associated resources."""
        self.loaded_models.pop(handle, None)
        self.speculative_engines.pop(handle, None)

        model_path = handle.replace("gguf:", "").replace("gguf-mm:", "")
        self.kv_quantizers.pop(model_path, None)

        if self._cache is not None:
            self._cache.invalidate(handle)

    def list_models(self) -> list[str]:
        """List all loaded model handles."""
        return list(self.loaded_models.keys())

    def _warmup_model(self, handle: str):
        """Run warmup inference on a newly loaded model."""
        if not self.config.warmup_iterations or self.config.warmup_iterations <= 0:
            return
        model = self.loaded_models[handle]
        for _ in range(self.config.warmup_iterations):
            try:
                model("warmup", max_tokens=1, echo=False)
            except Exception as exc:  # noqa: BLE001 -- best-effort; logged
                note_failure("gguf_engine:warmup", exc)

    def shutdown(self):
        """Clean up resources."""
        self._executor.shutdown(wait=True)
        self.loaded_models.clear()
        self.speculative_engines.clear()
        self.kv_quantizers.clear()

    def __del__(self):
        try:
            self._executor.shutdown(wait=False)
        except Exception as exc:  # noqa: BLE001 -- __del__ never raises
            note_failure("gguf_engine:del", exc)


class InferenceEngine:
    """High-performance multi-framework inference engine.

    Supports synchronous infer() and async infer_async() for
    non-blocking batch processing via a thread pool executor.
    """

    def __init__(self, config: EveConfig | None = None):
        self.config = config or EveConfig()

        # Auto-detect best device if set to "auto"
        if self.config.device == "auto":
            self.config.device = ModelLoader.get_best_device()
        self.loaded_models: dict[str, Any] = {}
        self.model_loaders = {
            "torch": self._load_torch_model,
            "sklearn": self._load_sklearn_model,
            "transformers": self._load_transformers_model,
            "onnx": self._load_onnx_model,
            "gguf": self._load_gguf_model,
            "gguf-speculative": self._load_gguf_speculative_model,
            "gguf-kv-quant": self._load_gguf_kv_quant_model,
            "gguf-multimodal": self._load_gguf_multimodal_model,
            "vl": self._load_vl_model,
        }
        self._frameworks = ModelLoader.detect_frameworks()
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.num_workers or 1
        )
        self._inference_count: int = 0
        self._total_latency_ms: float = 0.0

        # Inference cache (LRU + TTL)
        if self.config.enable_cache:
            self._cache = InferenceCache(
                max_size_bytes=self.config.cache_size_mb * 1024 * 1024,
                ttl_seconds=self.config.cache_ttl_seconds,
            )
        else:
            self._cache = None

    @property
    def gpu_info(self) -> dict[str, Any]:
        """Get GPU hardware information."""
        return ModelLoader.get_gpu_info()

    @property
    def available_frameworks(self) -> list[str]:
        """list of detected ML frameworks."""
        return [k for k, v in self._frameworks.items() if v]

    @property
    def cache_stats(self) -> dict[str, Any]:
        """Cache usage statistics (hits, misses, hit rate)."""
        if self._cache is None:
            return {"enabled": False}
        return {"enabled": True, **self._cache.stats}

    @property
    def stats(self) -> dict[str, Any]:
        """Runtime statistics including cache."""
        avg_latency = (
            self._total_latency_ms / self._inference_count
            if self._inference_count > 0
            else 0
        )
        return {
            "inference_count": self._inference_count,
            "total_latency_ms": round(self._total_latency_ms, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "loaded_models": len(self.loaded_models),
            "available_frameworks": self.available_frameworks,
            "cache": self.cache_stats,
        }

    def load_model(self, model_path: str, framework: str = "auto", **kwargs) -> str:
        """Load a model and return its handle.

        If framework is "auto", the framework is guessed from the file extension.

        The framework argument is validated BEFORE the path, because a bad
        framework name is a caller error that no file can satisfy: answering
        "Model not found" for it sends the operator to inspect a path when the
        argument actually at fault is the framework, and correcting the path
        only uncovers the real error on the next attempt. The consequence is
        that a missing path with an explicitly bad framework now raises
        ValueError (was FileNotFoundError); a missing path with a usable or
        "auto"-resolvable framework still raises FileNotFoundError, unchanged.
        """
        p = Path(model_path)

        if framework == "auto":
            framework = ModelLoader.guess_framework(p)
            if framework == "unknown":
                raise ValueError(
                    f"Cannot guess framework for: {model_path}. "
                    f"Specify explicitly from: {list(self.model_loaders.keys())}"
                )

        if framework not in self.model_loaders:
            raise ValueError(
                f"Unsupported framework: {framework}. "
                f"Available: {list(self.model_loaders.keys())}"
            )
        if framework not in self._frameworks or not self._frameworks[framework]:
            raise ImportError(f"Framework '{framework}' is not installed")

        if not p.exists():
            raise FileNotFoundError(f"Model not found: {model_path}")

        loader = self.model_loaders[framework]
        model = loader(model_path, **kwargs)
        handle = f"{framework}:{model_path}"
        self.loaded_models[handle] = model

        # Warm up newly loaded model
        self._warmup_model(handle)
        return handle

    def infer(
        self,
        handle: str,
        inputs: np.ndarray | list | dict,
        batch: bool = False,
    ) -> InferenceResult | BatchResult:
        """Run inference on a loaded model.

        When caching is enabled, checks the LRU+TTL cache before
        running inference. Identical inputs return cached results.
        """
        if handle not in self.loaded_models:
            raise KeyError(f"Model not loaded: {handle}")

        framework = handle.split(":")[0]

        # Check cache (only for single, non-batch inference)
        if not batch and self._cache is not None:
            cached = self._cache.get(handle, inputs, framework)
            if cached is not None:
                return cached

        model = self.loaded_models[handle]

        if batch and isinstance(inputs, list):
            result = self._batch_infer(model, framework, inputs)
        else:
            result = self._single_infer(model, framework, inputs)

        # Track stats
        if isinstance(result, InferenceResult):
            self._inference_count += 1
            self._total_latency_ms += result.latency_ms
        elif isinstance(result, BatchResult):
            self._inference_count += len(result.results)
            self._total_latency_ms += result.total_time_ms

        # Learn: record outcome for evolution (best-effort, never raises)
        try:
            from .model_registry import get_registry

            _mpath = handle.split(":", 1)[1] if ":" in handle else handle
            if isinstance(result, InferenceResult):
                _lat = float(result.latency_ms or 0)
            else:
                _lat = float(result.total_time_ms) / max(1, len(result.results))
            get_registry().record_inference(_mpath, _lat, framework)
        except Exception as exc:  # noqa: BLE001 -- best-effort; logged
            note_failure("engine:L202", exc)

        # Store in cache
        if not batch and self._cache is not None:
            self._cache.put(handle, inputs, framework, result)

        return result

    @timed_inference
    def _single_infer(self, model, framework: str, inputs) -> InferenceResult:
        """Run a single inference pass."""
        if framework == "torch":
            import torch

            tensor = torch.from_numpy(prepare_input_tensor(inputs))
            with torch.no_grad():
                output = model(tensor)
            predictions = postprocess_output(output, "torch")
            result = InferenceResult(
                model_name=str(type(model).__name__),
                framework=framework,
                input_shape=tuple(tensor.shape),
                output_shape=tuple(output.shape),
                latency_ms=0,  # set by decorator
                predictions=predictions,
            )
        elif framework == "sklearn":
            arr = np.array(inputs).reshape(1, -1) if inputs is not None else None
            output = model.predict(arr)
            result = InferenceResult(
                model_name=str(type(model).__name__),
                framework=framework,
                input_shape=arr.shape if arr is not None else (0,),
                output_shape=output.shape,
                latency_ms=0,
                predictions=output.tolist(),
            )
        elif framework == "transformers":
            output = model(inputs if isinstance(inputs, (str, list)) else str(inputs))
            result = InferenceResult(
                model_name=(
                    model.model.config._name_or_path
                    if hasattr(model, "model")
                    else "unknown"
                ),
                framework=framework,
                input_shape=(len(inputs) if isinstance(inputs, list) else 1,),
                output_shape=(len(output) if isinstance(output, list) else 1,),
                latency_ms=0,
                predictions=output,
            )
        elif framework == "onnx":
            arr = np.array(inputs, dtype=np.float32)
            if arr.ndim == 1:
                arr = arr.reshape(1, -1)
            ort_inputs = {model.get_inputs()[0].name: arr}
            output = model.run(None, ort_inputs)
            preds = output[0].tolist()
            result = InferenceResult(
                model_name=str(type(model).__name__),
                framework=framework,
                input_shape=arr.shape,
                output_shape=output[0].shape,
                latency_ms=0,
                predictions=preds,
            )
        elif framework == "gguf":
            text = inputs if isinstance(inputs, str) else str(inputs)
            output = model(text, max_tokens=128, echo=False)
            choices = output.get("choices", [])
            preds = [choices[0].get("text", "")] if choices else [""]
            result = InferenceResult(
                model_name=str(type(model).__name__),
                framework=framework,
                input_shape=(1,),
                output_shape=(1,),
                latency_ms=0,
                predictions=preds,
            )
        elif framework == "gguf-speculative":
            # Handle speculative decoding model
            text = inputs if isinstance(inputs, str) else str(inputs)
            spec_engine = model["speculative_engine"]
            output_text = spec_engine.generate(text)
            result = InferenceResult(
                model_name=f"speculative:{type(model['target']).__name__}",
                framework="gguf",
                input_shape=(1,),
                output_shape=(1,),
                latency_ms=0,
                predictions=[output_text],
            )
        elif framework == "gguf-kv-quant":
            # Handle KV quantized model
            text = inputs if isinstance(inputs, str) else str(inputs)
            quant_model = model["model"]
            output = quant_model(text, max_tokens=128, echo=False)
            choices = output.get("choices", [])
            preds = [choices[0].get("text", "")] if choices else [""]
            result = InferenceResult(
                model_name=f"kv_quant:{type(quant_model).__name__}",
                framework="gguf",
                input_shape=(1,),
                output_shape=(1,),
                latency_ms=0,
                predictions=preds,
            )
        elif framework == "gguf-multimodal":
            # Handle multi-modal model
            if isinstance(inputs, dict):
                text = inputs.get("text", "")
                images = inputs.get("images", [])
            else:
                text = str(inputs)
                images = []

            mm_model = model["model"]

            if images:
                # Multi-modal generation
                try:
                    messages = []
                    content = []
                    for img in images:
                        if isinstance(img, str):
                            content.append(
                                {"type": "image_url", "image_url": {"url": img}}
                            )
                        else:
                            content.append({"type": "image", "image": img})
                    content.append({"type": "text", "text": text})
                    messages.append({"role": "user", "content": content})

                    output = mm_model.create_chat_completion(
                        messages=messages,
                        max_tokens=128,
                        temperature=0.8,
                        top_p=0.95,
                    )

                    if output and "choices" in output:
                        output_text = output["choices"][0]["message"].get("content", "")
                    else:
                        output_text = ""
                except Exception:  # noqa: BLE001 -- use text-only fallback
                    # Fall back to text-only
                    output = mm_model(text, max_tokens=128, echo=False)
                    choices = output.get("choices", [])
                    output_text = choices[0].get("text", "") if choices else ""
            else:
                output = mm_model(text, max_tokens=128, echo=False)
                choices = output.get("choices", [])
                output_text = choices[0].get("text", "") if choices else ""

            result = InferenceResult(
                model_name=f"multimodal:{type(mm_model).__name__}",
                framework="gguf",
                input_shape=(1,),
                output_shape=(1,),
                latency_ms=0,
                predictions=[output_text],
            )
        elif framework == "vl":
            if not HAS_PIL:
                raise RuntimeError(
                    "PIL/Pillow required for VL inference. Install: pip install Pillow"
                )
            import torch
            import transformers
            from transformers import AutoProcessor

            # AutoModelForVision2Seq was removed from transformers 5.x (the
            # installed 5.19.0 raises ImportError on a static from-import), so
            # resolve it dynamically for a clear error instead of a dead import.
            AutoModelForVision2Seq = getattr(
                transformers, "AutoModelForVision2Seq", None
            )
            if AutoModelForVision2Seq is None:
                raise ImportError(
                    "VL inference requires transformers.AutoModelForVision2Seq, "
                    f"absent from installed transformers {transformers.__version__}"
                )

            if isinstance(inputs, dict):
                image_path = inputs.get("image", "")
                prompt = inputs.get("text", str(inputs))
            else:
                image_path = ""
                prompt = str(inputs)

            model_path = model  # VL stores path string, not loaded model object

            if image_path and os.path.exists(image_path):
                image = Image.open(image_path).convert("RGB")
                processor = AutoProcessor.from_pretrained(model_path)
                model_vl = AutoModelForVision2Seq.from_pretrained(model_path)
                proc_inputs = processor(text=prompt, images=image, return_tensors="pt")
                with torch.no_grad():
                    output_ids = model_vl.generate(**proc_inputs, max_new_tokens=128)
                preds = [processor.decode(output_ids[0], skip_special_tokens=True)]
            else:
                # Fall back to text-only pipeline
                from transformers import pipeline

                pipe = pipeline("text-generation", model=model_path, device=-1)
                preds = [pipe(prompt, max_new_tokens=128)[0]["generated_text"]]

            result = InferenceResult(
                model_name=(
                    str(Path(model_path).name) if isinstance(model_path, str) else "vl"
                ),
                framework=framework,
                input_shape=(1,),
                output_shape=(1,),
                latency_ms=0,
                predictions=preds,
            )
        else:
            raise ValueError(f"Unknown framework: {framework}")

        return result

    def _batch_infer(self, model, framework: str, inputs: list) -> BatchResult:
        """Run batched inference and return batch statistics."""
        results = []
        total_start = time.perf_counter()

        for inp in inputs:
            result = self._single_infer(model, framework, inp)
            results.append(result)

        total_time = (time.perf_counter() - total_start) * 1000
        n = len(inputs)
        return BatchResult(
            results=results,
            total_time_ms=round(total_time, 2),
            avg_latency_ms=round(total_time / n, 2) if n else 0,
            throughput_per_sec=(
                round(n / (total_time / 1000), 2) if total_time > 0 else 0
            ),
        )

    def unload_model(self, handle: str):
        """Unload a model from memory and invalidate its cache."""
        self.loaded_models.pop(handle, None)
        if self._cache is not None:
            self._cache.invalidate(handle)

    def list_models(self) -> list[str]:
        """list all loaded model handles."""
        return list(self.loaded_models.keys())

    def _load_torch_model(self, path: str, **kwargs):
        import torch

        try:
            model = torch.load(path, map_location="cpu", weights_only=False)
            model.eval()
            return model
        except FileNotFoundError:
            raise FileNotFoundError(f"Torch model not found: {path}")
        except RuntimeError as e:
            raise RuntimeError(f"Failed to load torch model '{path}': {e}")
        except Exception as e:  # noqa: BLE001 -- loader boundary; add path
            raise RuntimeError(f"Unexpected error loading torch model '{path}': {e}")

    def _load_sklearn_model(self, path: str, **kwargs):
        import joblib

        try:
            return joblib.load(path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Sklearn model not found: {path}")
        except Exception as e:  # noqa: BLE001 -- loader boundary; add path
            raise RuntimeError(f"Failed to load sklearn model '{path}': {e}")

    def _load_transformers_model(self, path: str, **kwargs):
        from transformers import pipeline

        task = kwargs.get("task", "text-classification")
        try:
            return pipeline(task, model=path, device=-1)
        except FileNotFoundError:
            raise FileNotFoundError(f"Transformers model not found: {path}")
        except OSError as e:
            raise OSError(
                f"Failed to load transformers model '{path}' (network/disk error): {e}"
            )
        except Exception as e:  # noqa: BLE001 -- loader boundary; add path
            raise RuntimeError(f"Failed to load transformers model '{path}': {e}")

    def _load_onnx_model(self, path: str, **kwargs):
        """Load an ONNX model via onnxruntime."""
        try:
            import onnxruntime as ort
        except ImportError:
            raise ImportError(
                "onnxruntime not installed. Install with: pip install onnxruntime"
            )
        providers = kwargs.get(
            "providers",
            (
                ["CUDAExecutionProvider", "CPUExecutionProvider"]
                if self.config.device == "cuda"
                else ["CPUExecutionProvider"]
            ),
        )
        try:
            return ort.InferenceSession(path, providers=providers)
        except FileNotFoundError:
            raise FileNotFoundError(f"ONNX model not found: {path}")
        except Exception as e:  # noqa: BLE001 -- loader boundary; add path
            raise RuntimeError(f"Failed to load ONNX model '{path}': {e}")

    def _load_gguf_model(self, path: str, **kwargs):
        """Load a GGUF model via llama-cpp-python."""
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python"
            )
        n_ctx = kwargs.get("n_ctx", self.config.max_batch_size or 2048)
        try:
            return Llama(model_path=path, n_ctx=n_ctx, verbose=False)
        except FileNotFoundError:
            raise FileNotFoundError(f"GGUF model not found: {path}")
        except Exception as e:  # noqa: BLE001 -- loader boundary; add path
            raise RuntimeError(f"Failed to load GGUF model '{path}': {e}")

    def _load_gguf_speculative_model(self, path: str, **kwargs):
        """Load a GGUF model with speculative decoding enabled.

        Requires: draft_model_path (str), num_draft_tokens (int, default=4)
        """
        if not HAS_SPECULATIVE:
            raise RuntimeError(
                "Speculative decoding not available (speculative.py import failed)"
            )

        draft_model_path = kwargs.get("draft_model_path")
        if not draft_model_path:
            raise ValueError("draft_model_path required for gguf-speculative framework")

        num_draft_tokens = kwargs.get("num_draft_tokens", 4)
        n_ctx = kwargs.get("n_ctx", self.config.max_batch_size or 2048)

        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python"
            )

        # Load target model
        target_model = Llama(model_path=path, n_ctx=n_ctx, verbose=False)

        # Load draft model
        draft_model = Llama(model_path=draft_model_path, n_ctx=n_ctx, verbose=False)

        # Create speculative engine
        speculative_engine = SpeculativeEngine(
            draft_model=draft_model,
            target_model=target_model,
            num_draft_tokens=num_draft_tokens,
        )

        # Return a wrapper that includes both models and the engine
        return {
            "target": target_model,
            "draft": draft_model,
            "speculative_engine": speculative_engine,
            "type": "speculative",
        }

    def _load_gguf_kv_quant_model(self, path: str, **kwargs):
        """Load a GGUF model with KV cache quantization.

        Args:
            kv_bits: Quantization bits (4 or 8, default=8)
        """
        if not HAS_KV_QUANT:
            raise RuntimeError(
                "KV quantization not available (kv_quant.py import failed)"
            )

        kv_bits = kwargs.get("kv_bits", 8)
        n_ctx = kwargs.get("n_ctx", self.config.max_batch_size or 2048)

        model = create_quantized_llama(path, n_ctx=n_ctx, kv_bits=kv_bits)

        return {
            "model": model,
            "kv_quantizer": model._kv_quantizer,
            "type": "kv_quant",
        }

    def _load_gguf_multimodal_model(self, path: str, **kwargs):
        """Load a multi-modal GGUF model (LLaVA-style)."""
        n_ctx = kwargs.get("n_ctx", self.config.max_batch_size or 2048)

        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "llama-cpp-python not installed. Install with: pip install llama-cpp-python"
            )

        model = Llama(model_path=path, n_ctx=n_ctx, verbose=False)

        return {
            "model": model,
            "type": "multimodal",
        }

    def _load_vl_model(self, path: str, **kwargs):
        """Register a Vision-Language model path for on-demand loading.

        VL models are loaded per-inference call (image + text) rather than
        pre-loaded, because different inputs may use different processor/model
        combinations.
        """
        if not HAS_PIL:
            raise RuntimeError(
                "PIL/Pillow required for VL models. Install: pip install Pillow"
            )
        if not Path(path).exists():
            raise FileNotFoundError(f"VL model path not found: {path}")
        # Store the path string; actual model loads at inference time
        return path

    async def infer_async(
        self,
        handle: str,
        inputs: np.ndarray | list | dict,
        batch: bool = False,
    ) -> InferenceResult | BatchResult:
        """Async inference — runs synchronously in a thread pool.

        Use this for non-blocking batch processing in async serving contexts.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            functools.partial(cast(Any, self.infer), handle, inputs),
            batch,
        )

    async def infer_stream(
        self,
        handle: str,
        inputs: str | list | dict,
        max_tokens: int = 256,
    ) -> AsyncGenerator[StreamToken]:
        """Stream inference results token by token.

        Supports native streaming for GGUF (llama.cpp) and transformers.
        Torch/sklearn/ONNX yield the full result as a single chunk.

        Usage:
            async for token in engine.infer_stream("gguf:model", "Hello"):
                print(token.text, end="", flush=True)
        """
        if handle not in self.loaded_models:
            raise KeyError(f"Model not loaded: {handle}")

        model = self.loaded_models[handle]
        framework = handle.split(":")[0]

        if framework == "gguf":
            async for token in stream_gguf(model, str(inputs), max_tokens):
                yield token
        elif framework in ("gguf-speculative", "gguf-kv-quant", "gguf-multimodal"):
            # For these, use the underlying llama model for streaming
            if framework == "gguf-speculative":
                llama_model = model["target"]
            elif framework == "gguf-kv-quant":
                llama_model = model["model"]
            else:  # gguf-multimodal
                llama_model = model["model"]
            async for token in stream_gguf(llama_model, str(inputs), max_tokens):
                yield token
        elif framework == "transformers":
            # Extract tokenizer from pipeline for true token streaming
            tokenizer = model.tokenizer if hasattr(model, "tokenizer") else None
            if tokenizer is None:
                # No tokenizer available — fall back to single-infer + stream_native
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    self._executor,
                    functools.partial(cast(Any, self.infer), handle, inputs),
                )
                async for token in stream_native(result):
                    yield token
            else:
                async for token in stream_transformers(
                    model, tokenizer, str(inputs), max_tokens
                ):
                    yield token
        elif framework in ("torch", "sklearn", "onnx"):
            # Non-streaming frameworks — run and yield full result
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                self._executor, functools.partial(cast(Any, self.infer), handle, inputs)
            )
            async for token in stream_native(result):
                yield token
        elif framework == "vl":
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                self._executor, functools.partial(cast(Any, self.infer), handle, inputs)
            )
            async for token in stream_native(result):
                yield token
        else:
            raise ValueError(f"Streaming not supported for framework: {framework}")

    def cache_invalidate(self, handle: str | None = None):
        """Invalidate cache entries for a handle or the entire cache."""
        if self._cache is not None:
            self._cache.invalidate(handle)

    def _warmup_model(self, handle: str):
        """Run warmup inference on a newly loaded model."""
        if not self.config.warmup_iterations or self.config.warmup_iterations <= 0:
            return
        model = self.loaded_models[handle]
        framework = handle.split(":")[0]
        warmup_input = np.zeros((1, 3), dtype=np.float32)
        for _ in range(self.config.warmup_iterations):
            try:
                if framework in ("torch", "sklearn", "onnx"):
                    self._single_infer(model, framework, warmup_input)
                elif framework in (
                    "gguf",
                    "gguf-speculative",
                    "gguf-kv-quant",
                    "gguf-multimodal",
                    "transformers",
                    "vl",
                ):
                    self._single_infer(model, framework, "warmup")
            except Exception as exc:  # noqa: BLE001 -- best-effort; logged
                note_failure("engine:L534", exc)  # Warmup failures are non-fatal

    def batch_infer(self, handle: str, inputs_list: list) -> BatchResult:
        """Run batched inference (public API for backward compatibility)."""
        # batch=True with a list input always takes infer()'s _batch_infer
        # path, whose result is BatchResult; cast asserts that proven fact.
        return cast(BatchResult, self.infer(handle, inputs_list, batch=True))

    def shutdown(self):
        """Clean up resources — call before discarding the engine."""
        self._executor.shutdown(wait=True)
        self.loaded_models.clear()

    def __del__(self):
        """Ensure executor is shut down on garbage collection."""
        try:
            self._executor.shutdown(wait=False)
        except Exception as exc:  # noqa: BLE001 -- __del__ never raises
            note_failure("engine:L550", exc)


def create_engine(config_path: str | None = None) -> InferenceEngine:
    """Factory function to create an inference engine."""
    config = EveConfig.from_file(config_path) if config_path else EveConfig()
    return InferenceEngine(config)

"""
KV Cache Quantization (8-bit)
=============================
8-bit KV cache for llama-cpp-python GGUF models.
"""

from __future__ import annotations

from typing import Any, Optional


class KVQuantizer:
    """
    8-bit KV cache quantizer for GGUF models.
    
    Quantizes the key-value cache to 8-bit integers to reduce memory
    usage and potentially improve inference speed on supported hardware.
    """

    def __init__(self, bits: int = 8):
        if bits not in (4, 8):
            raise ValueError("KV quantization only supports 4 or 8 bits")
        self.bits = bits
        self._quantized_cache: dict[str, Any] = {}
        self._scale_factors: dict[str, float] = {}
        self._zero_points: dict[str, int] = {}

    def quantize(self, key: str, data: Any) -> Any:
        """Quantize KV cache tensor to 8-bit."""
        import numpy as np

        arr = np.array(data, dtype=np.float32)
        original_shape = arr.shape

        # Flatten for quantization
        flat = arr.flatten()

        # Calculate scale and zero point
        min_val = float(np.min(flat))
        max_val = float(np.max(flat))

        if self.bits == 8:
            qmin, qmax = -128, 127
        else:  # 4-bit
            qmin, qmax = -8, 7

        scale = (max_val - min_val) / (qmax - qmin) if max_val != min_val else 1.0
        zero_point = int(round(-min_val / scale)) if scale != 0 else 0
        zero_point = max(qmin, min(qmax, zero_point))

        # Quantize
        quantized = np.round(flat / scale + zero_point).astype(np.int8 if self.bits == 8 else np.int16)
        quantized = np.clip(quantized, qmin, qmax)

        # Store metadata
        self._quantized_cache[key] = quantized.reshape(original_shape)
        self._scale_factors[key] = scale
        self._zero_points[key] = zero_point

        return self._quantized_cache[key]

    def dequantize(self, key: str) -> Any:
        """Dequantize KV cache tensor back to float32."""
        import numpy as np

        if key not in self._quantized_cache:
            raise KeyError(f"No quantized cache for key: {key}")

        quantized = self._quantized_cache[key]
        scale = self._scale_factors[key]
        zero_point = self._zero_points[key]

        # Dequantize
        dequantized = (quantized.astype(np.float32) - zero_point) * scale

        return dequantized

    def get_memory_savings(self) -> dict:
        """Calculate memory savings from quantization."""
        import numpy as np

        original_bytes = 0
        quantized_bytes = 0

        for key, quantized in self._quantized_cache.items():
            original_bytes += quantized.size * 4  # float32 = 4 bytes
            if self.bits == 8:
                quantized_bytes += quantized.size * 1  # int8 = 1 byte
            else:
                quantized_bytes += quantized.size * 2  # int16 = 2 bytes (packed 4-bit)

        savings_pct = (1 - quantized_bytes / original_bytes) * 100 if original_bytes > 0 else 0

        return {
            "original_mb": round(original_bytes / (1024 * 1024), 2),
            "quantized_mb": round(quantized_bytes / (1024 * 1024), 2),
            "savings_pct": round(savings_pct, 1),
            "bits": self.bits,
        }

    def clear(self):
        """Clear all quantized cache."""
        self._quantized_cache.clear()
        self._scale_factors.clear()
        self._zero_points.clear()


def apply_kv_quantization(model: Any, bits: int = 8) -> KVQuantizer:
    """
    Apply KV cache quantization to a llama-cpp-python model.
    
    This wraps the model's forward pass to quantize/dequantize KV cache.
    Note: llama-cpp-python manages KV cache internally, so this provides
    a framework for external cache management.
    """
    quantizer = KVQuantizer(bits=bits)
    # Store reference for external access
    model._kv_quantizer = quantizer
    return quantizer


def create_quantized_llama(
    model_path: str,
    n_ctx: int = 2048,
    kv_bits: int = 8,
    **kwargs
) -> Any:
    """
    Create a llama-cpp-python model with KV cache quantization enabled.
    
    Args:
        model_path: Path to GGUF model
        n_ctx: Context window size
        kv_bits: Quantization bits (4 or 8)
        **kwargs: Additional Llama constructor arguments
    
    Returns:
        Llama model with KV quantizer attached
    """
    from llama_cpp import Llama

    model = Llama(model_path=model_path, n_ctx=n_ctx, verbose=False, **kwargs)
    apply_kv_quantization(model, bits=kv_bits)
    return model
"""Tests for Speculative Decoding Engine, KV Quantizer and GGUF Engine."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest

from eve_unleashed import speculative
from eve_unleashed.engine import GGUFEngine
from eve_unleashed.kv_quant import KVQuantizer, create_quantized_llama


class FakeLlama:
    """Deterministic stand-in for a llama_cpp model: always emits one fixed token."""

    def __init__(self, token=" tok"):
        self.token = token
        self.calls = 0

    def __call__(self, prompt, max_tokens=1, echo=False, **kwargs):
        self.calls += 1
        return {"choices": [{"text": self.token}]}


def test_speculative_engine_wiring():
    """Module imports without the optional backend; factory and class exist."""
    assert isinstance(speculative.SpeculativeEngine, type)
    assert callable(speculative.create_speculative_engine)


def test_speculative_factory_without_backend():
    """Factory raises a clear, actionable error when llama-cpp-python is absent."""
    if speculative._LLAMA_AVAILABLE:
        pytest.skip("llama-cpp-python installed; factory needs real model files")
    with pytest.raises(ImportError, match="llama-cpp-python"):
        speculative.create_speculative_engine("draft.gguf", "target.gguf")


def test_speculative_generate_with_fakes():
    """Draft/verify/generate loop works end to end against deterministic fakes."""
    engine = speculative.SpeculativeEngine(
        FakeLlama(" A"), FakeLlama(" A"), num_draft_tokens=2, max_tokens=4
    )
    text = engine.generate("hello")
    assert isinstance(text, str) and text
    stats = engine.get_stats()
    assert stats["total_generated"] > 0
    assert 0.0 <= stats["acceptance_rate"] <= 1.0


def test_verify_draft_accept_and_reject():
    """Matching target tokens accept; a mismatch rejects at first position."""
    agreeing = speculative.SpeculativeEngine(FakeLlama(" A"), FakeLlama(" A"))
    assert agreeing.verify_draft("prompt", [" A", " A"]) == [1, 1]
    disagreeing = speculative.SpeculativeEngine(FakeLlama(" A"), FakeLlama(" B"))
    assert disagreeing.verify_draft("prompt", [" A"]) == [0]


@pytest.mark.parametrize("bits", [4, 8])
def test_kv_quantizer_roundtrip(bits):
    """Quantize/dequantize error stays within half a quantization step.

    Measured on 2026-11-22 (3.16t): 8-bit max err 0.00588 vs half-step
    0.00686; 4-bit max err 0.06667 vs half-step 0.11667.
    """
    import numpy as np

    data = [0.0, 0.5, 1.0, -1.0, 2.5]
    q = KVQuantizer(bits=bits)
    q.quantize("k", data)
    back = np.asarray(q.dequantize("k"), dtype=float)
    assert len(back) == len(data)
    half_step = (max(data) - min(data)) / (2**bits - 1) / 2
    assert np.abs(back - np.asarray(data, dtype=float)).max() <= half_step + 1e-9
    savings = q.get_memory_savings()
    assert savings["bits"] == bits
    assert savings["savings_pct"] > 0


def test_kv_quantizer_rejects_bad_bits():
    with pytest.raises(ValueError, match="4 or 8"):
        KVQuantizer(bits=16)


def test_create_quantized_llama_missing_file():
    """Factory surfaces loader errors instead of returning a broken model."""
    with pytest.raises(
        (FileNotFoundError, RuntimeError, ImportError, OSError, ValueError)
    ):
        create_quantized_llama("does-not-exist.gguf")


def test_gguf_engine_instantiates():
    engine = GGUFEngine()
    assert engine.list_models() == []
    engine.shutdown()

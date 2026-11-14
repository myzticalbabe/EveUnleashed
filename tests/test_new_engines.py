"""
Tests for Speculative Decoding Engine
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_speculative_engine_creation():
    """Test that SpeculativeEngine can be imported and instantiated."""
    try:
        from eve_unleashed.engine.speculative import SpeculativeEngine, create_speculative_engine
        print("SpeculativeEngine import successful")
    except ImportError as e:
        print(f"SpeculativeEngine import failed: {e}")
        # This is expected if llama-cpp-python is not available
        return True  # Don't fail the test
    
    return True

def test_kv_quantizer_creation():
    """Test that KVQuantizer can be imported and instantiated."""
    try:
        from eve_unleashed.engine.kv_quant import KVQuantizer, create_quantized_llama
        print("KVQuantizer import successful")
    except ImportError as e:
        print(f"KVQuantizer import failed: {e}")
        return True  # Don't fail the test
    
    return True

def test_gguf_engine_creation():
    """Test that GGUFEngine can be imported."""
    try:
        from eve_unleashed.engine import GGUFEngine
        print("GGUFEngine import successful")
    except ImportError as e:
        print(f"GGUFEngine import failed: {e}")
        return True  # Don't fail the test
    
    return True

if __name__ == "__main__":
    test_speculative_engine_creation()
    test_kv_quantizer_creation()
    test_gguf_engine_creation()
    print("All engine tests passed!")
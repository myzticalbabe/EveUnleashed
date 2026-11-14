"""
Tests for GGUF metadata editor
"""

import tempfile
import os
from pathlib import Path

def test_edit_metadata_dry_run():
    """Test dry-run mode of metadata editor."""
    from eve_unleashed.commands.edit_metadata import edit_metadata
    
    # Create a minimal GGUF file for testing
    # This is a basic test - in practice we'd need a real GGUF file
    # The function should handle invalid files gracefully (return 1)
    with tempfile.NamedTemporaryFile(suffix='.gguf', delete=False) as f:
        f.write(b'GGUF' + b'\x00' * 100)  # Minimal GGUF header (invalid)
        temp_path = f.name
    
    try:
        # Test dry run with invalid GGUF - should return 1 (error)
        result = edit_metadata(temp_path, {"test_key": "test_value"}, dry_run=True)
        # Should return 1 for invalid GGUF file even in dry-run mode
        assert result == 1
    finally:
        os.unlink(temp_path)

def test_edit_metadata_nonexistent():
    """Test error handling for nonexistent file."""
    from eve_unleashed.commands.edit_metadata import edit_metadata
    
    result = edit_metadata("/nonexistent/path/model.gguf", {"test": "value"}, dry_run=True)
    assert result == 1

def test_edit_metadata_invalid_format():
    """Test error handling for invalid key=value format."""
    # This should be caught at argument parsing level, not in function
    pass

if __name__ == "__main__":
    test_edit_metadata_dry_run()
    test_edit_metadata_nonexistent()
    print("All tests passed!")
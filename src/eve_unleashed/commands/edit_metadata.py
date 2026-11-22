"""
GGUF Metadata Editor CLI
========================
Edit GGUF model metadata: eve edit-metadata --model <gguf> --set key=val
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def edit_metadata(
    model_path: str, updates: dict[str, Any], dry_run: bool = False
) -> int:
    """Edit GGUF model metadata."""
    try:
        import gguf
    except ImportError:
        print(
            "ERROR: gguf library not installed. Install with: pip install gguf",
            file=sys.stderr,
        )
        return 1

    path = Path(model_path)
    if not path.exists():
        print(f"ERROR: Model not found: {model_path}", file=sys.stderr)
        return 1

    if not path.suffix.lower() == ".gguf":
        print(f"ERROR: Not a GGUF file: {model_path}", file=sys.stderr)
        return 1

    try:
        reader = gguf.GGUFReader(path)
    except Exception as e:  # noqa: BLE001 -- logged below, guard broad
        print(f"ERROR: Failed to read GGUF file: {e}", file=sys.stderr)
        return 1

    # Display current metadata
    print(f"=== Current metadata for {path.name} ===")
    for field in reader.fields.values():
        print(f"  {field.name}: {field.types} = {field.parts}")

    # Apply updates
    print("\n=== Applying updates ===")
    for key, value in updates.items():
        # Find the field
        found = False
        for field in reader.fields.values():
            if field.name == key:
                print(f"  {key}: {field.parts} -> {value}")
                found = True
                break
        if not found:
            print(f"  {key}: (new field) -> {value}")

    if dry_run:
        print("\n[DRY RUN] No changes written.")
        return 0

    # Write updated metadata
    try:
        # Create a new GGUF writer with updated metadata
        writer = gguf.GGUFWriter(str(path), "temp")

        # Copy all existing fields
        for field in reader.fields.values():
            if field.name in updates:
                # Use updated value
                writer.add_field(field.name, updates[field.name])
            else:
                # Keep original value
                writer.add_field(field.name, field.parts)

        # Add any new fields not in original
        for key, value in updates.items():
            if key not in reader.fields:
                writer.add_field(key, value)

        # Write to a temporary file first
        temp_path = path.with_suffix(".gguf.tmp")
        writer.write_header_to_file(str(temp_path))
        writer.write_kv_data_to_file(str(temp_path))
        writer.write_tensors_to_file(str(temp_path))
        writer.close()

        # Replace original
        temp_path.replace(path)
        print(f"\nUpdated {path.name} successfully.")

    except Exception as e:  # noqa: BLE001 -- logged below, guard broad
        print(f"ERROR: Failed to write GGUF file: {e}", file=sys.stderr)
        return 1

    return 0


def list_metadata(model_path: str) -> int:
    """List all metadata fields in a GGUF model."""
    try:
        import gguf
    except ImportError:
        print(
            "ERROR: gguf library not installed. Install with: pip install gguf",
            file=sys.stderr,
        )
        return 1

    path = Path(model_path)
    if not path.exists():
        print(f"ERROR: Model not found: {model_path}", file=sys.stderr)
        return 1

    try:
        reader = gguf.GGUFReader(path)
    except Exception as e:  # noqa: BLE001 -- logged below, guard broad
        print(f"ERROR: Failed to read GGUF file: {e}", file=sys.stderr)
        return 1

    print(f"=== Metadata for {path.name} ===")
    for field in reader.fields.values():
        print(f"  {field.name}: {field.types} = {field.parts}")

    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        prog="eve edit-metadata", description="Edit GGUF model metadata"
    )
    parser.add_argument("--model", "-m", required=True, help="Path to GGUF model")
    parser.add_argument(
        "--set", "-s", action="append", default=[], help="Key=value to set (repeatable)"
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List all metadata fields"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show changes without writing"
    )

    args = parser.parse_args()

    if args.list:
        sys.exit(list_metadata(args.model))

    if not args.set:
        print("ERROR: --set key=value required (or use --list)", file=sys.stderr)
        sys.exit(1)

    updates = {}
    for item in args.set:
        if "=" not in item:
            print(f"ERROR: Invalid format: {item} (use key=value)", file=sys.stderr)
            sys.exit(1)
        key, value = item.split("=", 1)
        # Try to parse as int/float/bool
        if value.lower() in ("true", "false"):
            value = value.lower() == "true"
        else:
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass  # Keep as string
        updates[key] = value

    sys.exit(edit_metadata(args.model, updates, args.dry_run))

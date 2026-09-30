"""Save generated media to timestamped files in a chosen directory."""

import base64
import sys
from datetime import datetime
from pathlib import Path


def output_path(prefix, ext, output_dir="."):
    """Return a unique <output_dir>/<prefix>_<timestamp>.<ext> path."""
    directory = Path(output_dir).expanduser()
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = directory / f"{prefix}_{stamp}.{ext}"
    counter = 1
    while path.exists():
        path = directory / f"{prefix}_{stamp}_{counter}.{ext}"
        counter += 1
    return path


def save_bytes(data, prefix, ext, output_dir="."):
    """Write bytes to a timestamped file and print where it went."""
    path = output_path(prefix, ext, output_dir)
    try:
        path.write_bytes(data)
    except OSError as e:
        print(f"ERROR: Failed to save {path}: {e}")
        print("\nPossible causes:")
        print("  - Insufficient permissions to write to the directory")
        print("  - Disk space full")
        print("  - Invalid output directory path")
        sys.exit(1)
    print(f"\nSaved to: {path.absolute()}")
    return path


def save_b64(data_b64, prefix, ext, output_dir="."):
    """Decode base64 media and save it."""
    return save_bytes(base64.b64decode(data_b64), prefix, ext, output_dir)


def ext_for_mime(mime, default):
    """Pick a file extension from a MIME type."""
    table = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/webp": "webp",
        "video/mp4": "mp4",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/wave": "wav",
    }
    return table.get((mime or "").lower(), default)

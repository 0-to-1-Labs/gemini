"""
Turn local files and URLs into Interactions API input parts.

Small files travel inline as base64. Large files go through the Files API,
which keeps them for 48 hours. YouTube links pass through as video URIs.
"""

import base64
import mimetypes
import re
import sys
import time
from pathlib import Path

# Above this size, upload through the Files API instead of sending inline.
INLINE_LIMIT_BYTES = 20 * 1024 * 1024

_EXTRA_MIME = {
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".webp": "image/webp",
    ".mkv": "video/x-matroska",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".aiff": "audio/aiff",
    ".md": "text/markdown",
}

_YOUTUBE = re.compile(r"^https?://(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)")


def mime_type(path):
    """Guess the MIME type of a file from its extension."""
    suffix = Path(path).suffix.lower()
    if suffix in _EXTRA_MIME:
        return _EXTRA_MIME[suffix]
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def kind_for(mime):
    """Map a MIME type to an Interactions API part type."""
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("video/"):
        return "video"
    if mime.startswith("audio/"):
        return "audio"
    return "document"


def require_file(path, label="File"):
    """Return a Path for an existing file, or exit with a clear message."""
    p = Path(path).expanduser()
    if not p.is_file():
        print(f"ERROR: {label} not found: {path}")
        sys.exit(1)
    return p


def read_b64(path):
    """Read a file and return its base64 text."""
    return base64.b64encode(Path(path).read_bytes()).decode("utf-8")


def is_youtube(url):
    return bool(_YOUTUBE.match(url or ""))


def youtube_part(url):
    """Build a video part for a public YouTube URL."""
    return {"type": "video", "uri": url}


def wait_active(client, file, poll_seconds=5):
    """Poll a Files API upload until it is ACTIVE. Exit if it FAILED."""
    while not file.state or file.state.name != "ACTIVE":
        if file.state and file.state.name == "FAILED":
            print(f"ERROR: Google could not process the uploaded file {file.name}.")
            sys.exit(1)
        print("Processing upload...")
        time.sleep(poll_seconds)
        file = client.files.get(name=file.name)
    return file


def upload(client, path):
    """Upload a file through the Files API and wait until it is usable."""
    p = require_file(path)
    print(f"Uploading {p.name} ({p.stat().st_size // (1024 * 1024)} MB) to the Files API...")
    uploaded = client.files.upload(file=str(p))
    return wait_active(client, uploaded)


def file_part(client, path, kind=None, force_upload=False, inline_limit=INLINE_LIMIT_BYTES):
    """Build an input part for a local file, inline or via the Files API."""
    p = require_file(path)
    mime = mime_type(p)
    part_type = kind or kind_for(mime)
    if force_upload or p.stat().st_size > inline_limit:
        uploaded = upload(client, p)
        return {"type": part_type, "uri": uploaded.uri, "mime_type": uploaded.mime_type or mime}
    return {"type": part_type, "data": read_b64(p), "mime_type": mime}


def image_parts(client, paths, limit=None, label="Reference image"):
    """Build image parts for a list of paths, enforcing an optional count limit."""
    paths = paths or []
    if limit is not None and len(paths) > limit:
        print(f"ERROR: Too many {label.lower()}s: {len(paths)} given, {limit} allowed.")
        sys.exit(1)
    parts = []
    for path in paths:
        p = require_file(path, label)
        mime = mime_type(p)
        if not mime.startswith("image/"):
            print(f"ERROR: {label} is not an image: {path}")
            sys.exit(1)
        parts.append(file_part(client, p, kind="image"))
    return parts

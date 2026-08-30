#!/usr/bin/env python3
"""
Nano Banana Pro Image Generator
Generates and edits images with Gemini, with Atlas Cloud as an optional
text-to-image provider.

Usage:
    python generate.py "An enhanced prompt describing the image"
    python generate.py "A 9:16 movie poster ..." --aspect-ratio 9:16 --resolution 2K
    python generate.py "Make the sky a dramatic sunset" --image photo.png
    python generate.py "A quick sketch of a fox" --fast
"""

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Nano Banana Pro (GA). Best for text rendering, reasoning, and high fidelity.
DEFAULT_MODEL = "gemini-3-pro-image"
# Nano Banana (Flash, GA). Faster and cheaper, good for drafts/iteration.
FAST_MODEL = "gemini-3.1-flash-image"
ATLAS_API_ROOT = "https://api.atlascloud.ai"
ATLAS_MODEL = "google/nano-banana-pro/text-to-image-developer"
ATLAS_USER_AGENT = "nanobanana/1.0"

ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
RESOLUTIONS = ["1K", "2K", "4K"]


def _pip_install(package):
    """Install a package, trying strategies that work in externally-managed envs."""
    for extra in (["--user"], ["--break-system-packages"], []):
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", *extra, package],
                capture_output=True,
                text=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            continue
    return False


def _ensure(import_callable, package):
    """Return the result of import_callable(), auto-installing `package` if needed.

    Installs and re-imports in the same process so the user never has to re-run
    the command after a first-time dependency install.
    """
    try:
        return import_callable()
    except ImportError:
        print(f"Required package '{package}' is not installed. Installing...")
        if not _pip_install(package):
            print(f"\nERROR: Failed to auto-install '{package}'.")
            print("\nPlease install it manually with one of:")
            print(f"  pip install --user {package}")
            print(f"  pip install --break-system-packages {package}")
            print("\nOr use a virtual environment:")
            print("  python3 -m venv venv && source venv/bin/activate")
            print(f"  pip install {package}")
            sys.exit(1)
        importlib.invalidate_caches()
        try:
            return import_callable()
        except ImportError:
            print(f"\nInstalled '{package}', but it is not importable in this "
                  f"interpreter ({sys.executable}).")
            print("If you use a virtualenv or pyenv, install it there and re-run.")
            sys.exit(1)


def _import_genai():
    from google import genai
    from google.genai import types
    return genai, types


def _import_pil():
    from PIL import Image
    return Image


def validate_api_key():
    """Validate that the GEMINI_API_KEY environment variable is set."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        print("\nTo fix this, set your API key:")
        print("  export GEMINI_API_KEY='your-api-key-here'")
        print("\nGet your API key at: https://aistudio.google.com/apikey")
        sys.exit(1)
    return api_key


def validate_atlas_api_key():
    """Return the Atlas Cloud API key from either supported variable name."""
    api_key = os.getenv("ATLASCLOUD_API_KEY") or os.getenv("ATLAS_CLOUD_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ATLASCLOUD_API_KEY (or ATLAS_CLOUD_API_KEY) is not set."
        )
    return api_key


def _atlas_request(path, api_key=None, payload=None):
    """Build an Atlas request with headers that also work behind its CDN."""
    headers = {
        "Accept": "application/json",
        "User-Agent": ATLAS_USER_AGENT,
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    return urllib.request.Request(
        f"{ATLAS_API_ROOT}{path}", data=data, headers=headers
    )


def _atlas_json_request(request, transient_retries=0):
    """Read JSON, retrying only when the caller explicitly permits it."""
    for attempt in range(transient_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            transient = exc.code == 429 or 500 <= exc.code < 600
            if not transient or attempt == transient_retries:
                detail = exc.read().decode("utf-8", errors="replace")[:300]
                raise RuntimeError(f"Atlas API HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            if attempt == transient_retries:
                raise RuntimeError(f"Atlas API network error: {exc.reason}") from exc
        time.sleep(min(2 ** attempt, 4))


def _atlas_data(response):
    """Unwrap Atlas' standard response envelope when present."""
    if isinstance(response, dict) and isinstance(response.get("data"), (dict, list)):
        return response["data"]
    return response


def validate_atlas_model(model):
    """Confirm the requested image model is currently available in the catalog."""
    catalog = _atlas_data(
        _atlas_json_request(_atlas_request("/api/v1/models"), transient_retries=2)
    )
    match = next(
        (item for item in catalog if item.get("model") == model),
        None,
    )
    if not match or not match.get("display_console", True):
        raise RuntimeError(f"Atlas model is not currently available: {model}")
    if "TEXT-TO-IMAGE" not in match.get("categories", []):
        raise RuntimeError(f"Atlas model is not a text-to-image model: {model}")


def _image_suffix(content):
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return ".webp"
    raise RuntimeError("Atlas output is not a recognized PNG, JPEG, or WebP image.")


def _download_atlas_image(url):
    request = urllib.request.Request(url, headers={"User-Agent": ATLAS_USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise RuntimeError(f"Could not download Atlas output: {exc}") from exc
    return content, _image_suffix(content)


def generate_atlas_image(prompt, model, aspect_ratio=None, resolution=None):
    """Generate one image through Atlas Cloud without retrying the paid POST."""
    api_key = validate_atlas_api_key()
    validate_atlas_model(model)
    payload = {"model": model, "prompt": prompt}
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if resolution:
        payload["resolution"] = resolution.lower()

    print(f"Generating image with Atlas Cloud ({model})...")
    created = _atlas_data(
        _atlas_json_request(
            _atlas_request("/api/v1/model/generateImage", api_key, payload),
            transient_retries=0,
        )
    )
    request_id = created.get("id") if isinstance(created, dict) else None
    if not request_id:
        raise RuntimeError("Atlas generation response did not include a request id.")

    for poll_number in range(60):
        prediction = _atlas_data(
            _atlas_json_request(
                _atlas_request(f"/api/v1/model/prediction/{request_id}", api_key),
                transient_retries=2,
            )
        )
        status = prediction.get("status", "").lower()
        if status in {"completed", "succeeded", "success"}:
            outputs = prediction.get("outputs") or []
            if not outputs:
                raise RuntimeError("Atlas generation completed without an output URL.")
            print("Image generated successfully!")
            return _download_atlas_image(outputs[0])
        if status in {"failed", "canceled", "cancelled"}:
            raise RuntimeError(
                prediction.get("error") or f"Atlas generation ended with status: {status}"
            )
        if poll_number < 59:
            time.sleep(3)
    raise RuntimeError("Atlas generation timed out while waiting for completion.")


def load_reference_images(paths):
    """Load reference/input images for editing, as PIL.Image objects."""
    if not paths:
        return []
    Image = _ensure(_import_pil, "pillow")
    images = []
    for path in paths:
        p = Path(path)
        if not p.is_file():
            print(f"ERROR: Reference image not found: {path}")
            sys.exit(1)
        try:
            images.append(Image.open(p))
        except Exception as e:
            print(f"ERROR: Could not open reference image '{path}': {e}")
            sys.exit(1)
    return images


def generate_image(prompt, model, aspect_ratio=None, resolution=None, reference_images=None):
    """
    Generate (or edit) an image using Nano Banana Pro / Nano Banana.

    Args:
        prompt: The enhanced image generation prompt.
        model: The Gemini image model ID to use.
        aspect_ratio: Optional aspect ratio string (e.g. "16:9").
        resolution: Optional output resolution ("1K", "2K", "4K").
        reference_images: Optional list of PIL.Image objects to edit/combine.

    Returns:
        Image object or None if generation failed.
    """
    genai, types = _ensure(_import_genai, "google-genai")
    try:
        api_key = validate_api_key()
        client = genai.Client(api_key=api_key)

        label = "Nano Banana" if model == FAST_MODEL else "Nano Banana Pro"
        action = "Editing" if reference_images else "Generating"
        print(f"{action} image with {label} ({model})...")
        print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
        if aspect_ratio or resolution:
            print(f"Output: aspect_ratio={aspect_ratio or 'default'}, "
                  f"resolution={resolution or 'default'}")
        if reference_images:
            print(f"Reference images: {len(reference_images)}")
        print()

        # Build the optional image_config (aspect ratio / resolution).
        image_config_kwargs = {}
        if aspect_ratio:
            image_config_kwargs["aspect_ratio"] = aspect_ratio
        if resolution:
            image_config_kwargs["image_size"] = resolution

        config = None
        if image_config_kwargs:
            config = types.GenerateContentConfig(
                image_config=types.ImageConfig(**image_config_kwargs)
            )

        # Text prompt first, then any reference images for editing.
        contents = [prompt, *(reference_images or [])]

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        parts = getattr(response, "parts", None) or []
        for part in parts:
            if getattr(part, "text", None):
                print(f"Model response: {part.text}")
            elif getattr(part, "inline_data", None) is not None:
                print("Image generated successfully!")
                return part.as_image()

        print("ERROR: No image data found in API response.")
        print("The model may have refused the request or returned text only.")
        return None

    except Exception as e:
        print(f"ERROR: Failed to generate image: {str(e)}")

        error_str = str(e).lower()
        if "api key" in error_str or "authentication" in error_str:
            print("\nPossible causes:")
            print("  - Invalid API key")
            print("  - API key not properly set in GEMINI_API_KEY environment variable")
            print("  - API key may have been revoked or expired")
        elif "quota" in error_str or "rate limit" in error_str:
            print("\nPossible causes:")
            print("  - API quota exceeded")
            print("  - Rate limit reached")
            print("  - Try again in a few moments")
        elif "not found" in error_str or "model" in error_str:
            print("\nPossible causes:")
            print(f"  - The model '{model}' is not available to your API key/region")
            print("  - Try the default Pro model, or '--fast' for the Flash model")
        elif "network" in error_str or "connection" in error_str:
            print("\nPossible causes:")
            print("  - Network connectivity issues")
            print("  - Firewall blocking API requests")
            print("  - Check your internet connection")

        return None


def save_image(image, output_dir=".", suffix=".png"):
    """Save the generated image to a timestamped PNG file."""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nanobanana_{timestamp}{suffix}"
        filepath = Path(output_dir) / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        if hasattr(image, "save"):
            try:
                image.save(filepath, "PNG")
            except TypeError:
                # Gemini Image object takes only filepath
                image.save(str(filepath))
        else:
            # Fallback for raw bytes
            with open(filepath, "wb") as f:
                f.write(image)
        print(f"\nImage saved to: {filepath.absolute()}")
        return filepath

    except Exception as e:
        print(f"ERROR: Failed to save image: {str(e)}")
        print("\nPossible causes:")
        print("  - Insufficient permissions to write to the directory")
        print("  - Disk space full")
        print("  - Invalid output directory path")
        return None


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate or edit images with Nano Banana Pro.",
    )
    parser.add_argument("prompt", nargs="+", help="The enhanced image prompt.")
    parser.add_argument(
        "--provider",
        choices=["gemini", "atlas"],
        default="gemini",
        help="Image provider. Gemini remains the default.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help=f"Use the faster, cheaper Flash model ({FAST_MODEL}) instead of Pro.",
    )
    parser.add_argument(
        "--model",
        help=f"Explicit model ID (overrides --fast). Default: {DEFAULT_MODEL}.",
        default=None,
    )
    parser.add_argument(
        "--aspect-ratio",
        choices=ASPECT_RATIOS,
        help="Output aspect ratio (e.g. 16:9, 9:16, 1:1).",
    )
    parser.add_argument(
        "--resolution",
        choices=RESOLUTIONS,
        help="Output resolution. Default is the model default (1K).",
    )
    parser.add_argument(
        "--image",
        action="append",
        metavar="PATH",
        help="Reference/input image to edit or combine. Repeatable.",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory to save the image (default: current directory).",
    )
    return parser.parse_args(argv)


def resolve_options(args):
    """Resolve provider-specific options without changing Gemini defaults."""
    if args.provider == "atlas":
        if args.fast:
            raise ValueError("--fast is only available with the Gemini provider.")
        if args.image:
            raise ValueError(
                "The Atlas text-to-image provider does not support --image."
            )
        return args.model or ATLAS_MODEL
    return args.model or (FAST_MODEL if args.fast else DEFAULT_MODEL)


def main():
    args = parse_args()

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        print("ERROR: Prompt cannot be empty.")
        sys.exit(1)

    try:
        model = resolve_options(args)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        sys.exit(2)

    suffix = ".png"
    if args.provider == "atlas":
        try:
            image, suffix = generate_atlas_image(
                prompt,
                model=model,
                aspect_ratio=args.aspect_ratio,
                resolution=args.resolution,
            )
        except RuntimeError as exc:
            print(f"ERROR: {exc}")
            sys.exit(1)
    else:
        reference_images = load_reference_images(args.image)
        image = generate_image(
            prompt,
            model=model,
            aspect_ratio=args.aspect_ratio,
            resolution=args.resolution,
            reference_images=reference_images,
        )
    if image is None:
        sys.exit(1)

    filepath = save_image(image, output_dir=args.output_dir, suffix=suffix)
    if filepath is None:
        sys.exit(1)

    print("\n✓ Image generation complete!")
    print(f"✓ Saved as: {filepath.name}")


if __name__ == "__main__":
    main()

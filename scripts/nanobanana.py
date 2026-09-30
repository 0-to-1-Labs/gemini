#!/usr/bin/env python3
"""
Nano Banana image generator (gemini:nanobanana)
Generates and edits images with the Gemini image models via the
Interactions API.

Usage:
    python nanobanana.py "An enhanced prompt describing the image"
    python nanobanana.py "A 9:16 movie poster ..." --aspect-ratio 9:16 --resolution 2K
    python nanobanana.py "Make the sky a dramatic sunset" --image photo.png
    python nanobanana.py "A quick sketch of a fox" --fast
"""

import argparse
import base64
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import client as gc  # noqa: E402
from lib import media, output  # noqa: E402

# Nano Banana Pro (GA). Best for text rendering, reasoning, and high fidelity.
DEFAULT_MODEL = "gemini-3-pro-image"
# Nano Banana 2 (Flash, GA). Faster and cheaper, good for drafts/iteration.
FAST_MODEL = "gemini-3.1-flash-image"
# Nano Banana 2 Lite (GA). Cheapest, 1K only.
LITE_MODEL = "gemini-3.1-flash-lite-image"

LABELS = {
    DEFAULT_MODEL: "Nano Banana Pro",
    FAST_MODEL: "Nano Banana 2",
    LITE_MODEL: "Nano Banana 2 Lite",
}

ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"]
RESOLUTIONS = ["1K", "2K", "4K"]
THINKING_LEVELS = ["minimal", "high"]


def generate_image(client, prompt, model, aspect_ratio=None, resolution=None,
                   reference_images=None, thinking=None):
    """Generate (or edit) an image. Returns the interaction, or None on failure."""
    label = LABELS.get(model, model)
    action = "Editing" if reference_images else "Generating"
    print(f"{action} image with {label} ({model})...")
    print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    if aspect_ratio or resolution:
        print(f"Output: aspect_ratio={aspect_ratio or 'default'}, "
              f"resolution={resolution or 'default'}")
    if reference_images:
        print(f"Reference images: {len(reference_images)}")
    print()

    # The image models only emit JPEG; --png re-encodes locally after the call.
    response_format = {"type": "image", "mime_type": "image/jpeg"}
    if aspect_ratio:
        response_format["aspect_ratio"] = aspect_ratio
    if resolution:
        response_format["image_size"] = resolution

    generation_config = {"thinking_level": thinking} if thinking else None

    # Text prompt first, then any reference images for editing.
    contents = [{"type": "text", "text": prompt}, *(reference_images or [])]

    try:
        return client.interactions.create(
            model=model,
            input=contents,
            response_format=response_format,
            generation_config=generation_config,
        )
    except Exception as e:
        return gc.explain_error(
            e, model,
            fallback_hint="Try the default Pro model, or '--fast' for the Flash model",
        )


def _import_pil():
    from PIL import Image
    return Image


def to_png(jpeg_bytes):
    """Re-encode JPEG bytes as PNG with Pillow."""
    Image = gc.ensure(_import_pil, "pillow")
    with Image.open(io.BytesIO(jpeg_bytes)) as im:
        buf = io.BytesIO()
        im.save(buf, "PNG")
        return buf.getvalue()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate or edit images with Nano Banana Pro (Gemini 3 Pro Image).",
    )
    parser.add_argument("prompt", nargs="+", help="The enhanced image prompt.")
    parser.add_argument(
        "--fast",
        action="store_true",
        help=f"Use the faster, cheaper Flash model ({FAST_MODEL}) instead of Pro.",
    )
    parser.add_argument(
        "--lite",
        action="store_true",
        help=f"Use the cheapest Lite model ({LITE_MODEL}). 1K output only.",
    )
    parser.add_argument(
        "--model",
        help=f"Explicit model ID (overrides --fast/--lite). Default: {DEFAULT_MODEL}.",
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
        "--png",
        action="store_true",
        help="Re-encode the JPEG output as PNG (needs pillow, auto-installed).",
    )
    parser.add_argument(
        "--thinking",
        choices=THINKING_LEVELS,
        help="Thinking level (Flash models only). 'high' for complex scenes.",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
        help="Directory to save the image (default: current directory).",
    )
    return parser.parse_args(argv)


def main():
    args = parse_args()

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        gc.fail("Prompt cannot be empty.")

    if args.model:
        model = args.model
    elif args.lite:
        model = LITE_MODEL
    elif args.fast:
        model = FAST_MODEL
    else:
        model = DEFAULT_MODEL

    if args.lite and args.resolution and args.resolution != "1K":
        gc.fail("The Lite model only produces 1K images. Drop --resolution or use --fast.")

    client = gc.get_client()
    reference_images = media.image_parts(client, args.image)

    interaction = generate_image(
        client,
        prompt,
        model=model,
        aspect_ratio=args.aspect_ratio,
        resolution=args.resolution,
        reference_images=reference_images,
        thinking=args.thinking,
    )
    if interaction is None:
        sys.exit(1)

    text = gc.output_text(interaction)
    if text:
        print(f"Model response: {text}")

    image = getattr(interaction, "output_image", None)
    if image is None or not getattr(image, "data", None):
        gc.fail("No image data found in API response.",
                ["The model may have refused the request or returned text only."])

    data = base64.b64decode(image.data)
    ext = output.ext_for_mime(getattr(image, "mime_type", None), "jpg")
    if args.png:
        data, ext = to_png(data), "png"
    filepath = output.save_bytes(data, "nanobanana", ext, args.output_dir)

    print("\n✓ Image generation complete!")
    print(f"✓ Saved as: {filepath.name}")


if __name__ == "__main__":
    main()

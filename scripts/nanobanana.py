#!/usr/bin/env python3
"""
Nano Banana image generator (gemini:nanobanana)
Generates and edits images with the Gemini image models via the
Interactions API.

Usage:
    python3 nanobanana.py --prompt-file prompt.txt
    python3 nanobanana.py --prompt-file prompt.txt --aspect-ratio 9:16 --resolution 2K
    python3 nanobanana.py --prompt-file prompt.txt --image photo.png
    python3 nanobanana.py - --fast <<'PROMPT'
    A quick sketch of a fox
    PROMPT
    python3 nanobanana.py 'An enhanced prompt describing the image'

Prefer --prompt-file or stdin (-). A prompt on the command line goes through
the shell, which expands $, backticks and backslashes inside double quotes.
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

ASPECT_RATIOS = ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9",
                 "1:4", "4:1", "1:8", "8:1"]
# 512 is Flash only; Lite is 1K only; Pro is 1K, 2K, 4K.
RESOLUTIONS = ["512", "1K", "2K", "4K"]
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


def output_images(interaction):
    """Return every image the model produced, oldest first.

    interaction.output_image holds only the last image, so walk the model
    output steps to catch multi-image responses.
    """
    images = []
    for step in getattr(interaction, "steps", None) or []:
        if getattr(step, "type", None) != "model_output":
            continue
        for item in getattr(step, "content", None) or []:
            if getattr(item, "type", None) == "image" and getattr(item, "data", None):
                images.append(item)
    last = getattr(interaction, "output_image", None)
    if not images and last is not None and getattr(last, "data", None):
        images.append(last)
    return images


def explain_empty(interaction):
    """Exit with the status and errors of an interaction that returned no image."""
    hints = ["The model may have refused the request or returned text only."]
    status = getattr(interaction, "status", None)
    if status:
        hints.append(f"Interaction status: {status}")
    for err in getattr(interaction, "errors", None) or []:
        code = getattr(err, "code", None)
        message = getattr(err, "message", None)
        hints.append(f"API error: {code or ''} {message or ''}".strip())
    gc.fail("No image data found in API response.", hints)


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


def read_prompt(args):
    """Return the prompt from --prompt-file, stdin (-), or the command line."""
    if args.prompt_file and args.prompt:
        gc.fail("Pass the prompt once: either --prompt-file or on the command line.")
    source = args.prompt_file
    if not source and args.prompt == ["-"]:
        source = "-"
    if source == "-":
        text = sys.stdin.read()
    elif source:
        try:
            text = Path(source).expanduser().read_text(encoding="utf-8")
        except OSError as e:
            gc.fail(f"Could not read prompt file {source}: {e}")
    else:
        text = " ".join(args.prompt)
    text = text.strip()
    if not text:
        gc.fail("Prompt cannot be empty. Use --prompt-file PATH, '-' for stdin, "
                "or a quoted prompt.")
    return text


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate or edit images with Nano Banana Pro (Gemini 3 Pro Image).",
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="The enhanced image prompt, or '-' to read it from stdin. "
             "Prefer --prompt-file so the shell never expands the text.",
    )
    parser.add_argument(
        "--prompt-file",
        metavar="PATH",
        help="Read the prompt from a UTF-8 text file ('-' for stdin).",
    )
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

    prompt = read_prompt(args)

    if args.model:
        model = args.model
    elif args.lite:
        model = LITE_MODEL
    elif args.fast:
        model = FAST_MODEL
    else:
        model = DEFAULT_MODEL

    if model == LITE_MODEL and args.resolution and args.resolution != "1K":
        gc.fail("The Lite model only produces 1K images. Drop --resolution or use --fast.")
    if model == DEFAULT_MODEL and args.resolution == "512":
        gc.fail("The Pro model does not produce 512px images. Use --fast, or 1K/2K/4K.")

    client = gc.get_client()
    if args.png:
        gc.ensure(_import_pil, "pillow")  # Before the paid call, not after.
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

    images = output_images(interaction)
    if not images:
        explain_empty(interaction)

    saved = []
    for image in images:
        data = base64.b64decode(image.data)
        ext = output.ext_for_mime(getattr(image, "mime_type", None), "jpg")
        if args.png:
            data, ext = to_png(data), "png"
        saved.append(output.save_bytes(data, "nanobanana", ext, args.output_dir))

    print("\n✓ Image generation complete!")
    for filepath in saved:
        print(f"✓ Saved as: {filepath.name}")


if __name__ == "__main__":
    main()

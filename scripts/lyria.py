#!/usr/bin/env python3
"""
Lyria music generator (gemini:lyria)
Generates a full song with lyrics from a text prompt.

Usage:
    python lyria.py "An upbeat indie-pop song about a road trip at sunrise"
    python lyria.py "A calm solo piano piece, instrumental, about two minutes" --wav
    python lyria.py "A song that matches the mood of this photo" --image beach.jpg
"""

import argparse
import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import client as gc  # noqa: E402
from lib import media, output  # noqa: E402

DEFAULT_MODEL = os.getenv("GEMINI_LYRIA_MODEL", "lyria-3.5")
MAX_IMAGES = 10


def generate_music(client, prompt, model, parts, wav=False):
    """Run one Lyria interaction. Returns the interaction, or None on failure."""
    print(f"Composing with Lyria ({model})...")
    print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print()
    kwargs = {"model": model, "input": [{"type": "text", "text": prompt}, *parts]}
    if wav:
        # Default output is MP3; requesting an audio response_format selects WAV.
        kwargs["response_format"] = {"type": "audio"}
    try:
        return client.interactions.create(**kwargs)
    except Exception as e:
        return gc.explain_error(
            e, model,
            fallback_hint="Check the models page for the current Lyria model IDs",
        )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate a song with Lyria.")
    parser.add_argument("prompt", nargs="+",
                        help="Genre, mood, tempo, instruments, lyrics, structure tags like [Chorus].")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model ID. Default: {DEFAULT_MODEL}.")
    parser.add_argument("--wav", action="store_true", help="Output WAV instead of MP3.")
    parser.add_argument("--image", action="append", metavar="PATH",
                        help=f"Mood reference image, up to {MAX_IMAGES}. Repeatable.")
    parser.add_argument("--output-dir", default=".",
                        help="Directory to save the song (default: current directory).")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    prompt = " ".join(args.prompt).strip()
    if not prompt:
        gc.fail("Prompt cannot be empty.")

    client = gc.get_client()
    parts = media.image_parts(client, args.image, MAX_IMAGES, "Reference image")

    interaction = generate_music(client, prompt, args.model, parts, wav=args.wav)
    if interaction is None:
        sys.exit(1)

    audio = getattr(interaction, "output_audio", None)
    if audio is None or not getattr(audio, "data", None):
        gc.fail("No audio in API response.",
                ["The model may have refused the request or returned text only."])

    ext = output.ext_for_mime(getattr(audio, "mime_type", None), "wav" if args.wav else "mp3")
    path = output.save_bytes(base64.b64decode(audio.data), "lyria", ext, args.output_dir)

    lyrics = gc.output_text(interaction)
    if lyrics:
        print(f"\nLyrics:\n{lyrics}")

    print("\n✓ Music generation complete!")
    print(f"✓ Saved as: {path.name}")


if __name__ == "__main__":
    main()

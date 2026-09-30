#!/usr/bin/env python3
"""
Gemini media understanding (gemini:understand)
Asks a Gemini model about video, audio, images, PDFs, or YouTube links.

Usage:
    python understand.py "Summarize this meeting" --file recording.mp4
    python understand.py "List every action item with a timestamp" --file call.m4a
    python understand.py "What does section 3 require?" --file contract.pdf
    python understand.py "Summarize in five bullets" --url https://www.youtube.com/watch?v=...
    python understand.py --transcribe --file interview.mp3 --out transcript.md
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import client as gc  # noqa: E402
from lib import media  # noqa: E402

DEFAULT_MODEL = os.getenv("GEMINI_UNDERSTAND_MODEL", "gemini-3.8-flash")
TRANSCRIBE_MODEL = "gemini-3.5-transcribe"
TRANSCRIBE_PROMPT = ("Transcribe this audio verbatim. Label each speaker and add a "
                     "timestamp at the start of each turn.")
MAX_YOUTUBE = 10


def video_processing(fps, start, end):
    """Build the optional processing block for video parts."""
    block = {}
    if fps:
        block["fps"] = fps
    if start is not None:
        block["start_offset"] = start
    if end is not None:
        block["end_offset"] = end
    if block:
        block["type"] = "static"
    return block


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Analyze media files with Gemini.")
    parser.add_argument("prompt", nargs="*", help="Question or instruction about the media.")
    parser.add_argument("--file", action="append", metavar="PATH",
                        help="Video, audio, image, or PDF. Repeatable. Large files upload automatically.")
    parser.add_argument("--url", action="append", metavar="YOUTUBE_URL",
                        help=f"Public YouTube link. Repeatable, up to {MAX_YOUTUBE}.")
    parser.add_argument("--transcribe", action="store_true",
                        help=f"Use {TRANSCRIBE_MODEL} with a transcription prompt.")
    parser.add_argument("--model", default=None, help=f"Model ID. Default: {DEFAULT_MODEL}.")
    parser.add_argument("--fps", type=float, help="Video sampling rate. Default 1 frame per second.")
    parser.add_argument("--start", type=int, metavar="SECONDS", help="Video clip start.")
    parser.add_argument("--end", type=int, metavar="SECONDS", help="Video clip end.")
    parser.add_argument("--out", metavar="PATH", help="Write the answer to this file too.")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    prompt = " ".join(args.prompt).strip()
    if args.transcribe and not prompt:
        prompt = TRANSCRIBE_PROMPT
    if not prompt:
        gc.fail("Prompt cannot be empty.")
    if not args.file and not args.url:
        gc.fail("Give at least one --file or --url.")
    if args.url and len(args.url) > MAX_YOUTUBE:
        gc.fail(f"Too many URLs: {len(args.url)} given, {MAX_YOUTUBE} allowed.")

    model = args.model or (TRANSCRIBE_MODEL if args.transcribe else DEFAULT_MODEL)
    client = gc.get_client()

    processing = video_processing(args.fps, args.start, args.end)
    parts = []
    for path in args.file or []:
        part = media.file_part(client, path)
        if part["type"] == "video" and processing:
            part["processing"] = processing
        parts.append(part)
    for url in args.url or []:
        if not media.is_youtube(url):
            gc.fail(f"Not a YouTube URL: {url}", ["Only public YouTube links are supported."])
        part = media.youtube_part(url)
        if processing:
            part["processing"] = processing
        parts.append(part)

    print(f"Analyzing {len(parts)} input(s) with {model}...")
    print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print()

    try:
        interaction = client.interactions.create(
            model=model,
            input=[*parts, {"type": "text", "text": prompt}],
        )
    except Exception as e:
        gc.explain_error(e, model, fallback_hint=f"Try --model {DEFAULT_MODEL}")
        sys.exit(1)

    answer = gc.output_text(interaction)
    if not answer:
        gc.fail("The model returned no text.")

    print(answer)
    if args.out:
        out = Path(args.out).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(answer + "\n", encoding="utf-8")
        print(f"\nSaved to: {out.absolute()}")


if __name__ == "__main__":
    main()

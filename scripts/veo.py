#!/usr/bin/env python3
"""
Veo 3.1 video generator (gemini:veo)
Generates 4, 6, or 8 second cinematic clips with native audio.

Google retires every Veo 3.1 model on 2026-10-22. Use gemini:omni after that.

Usage:
    python veo.py "A golden retriever running through autumn leaves, slow motion"
    python veo.py "The fish swims toward the camera" --image fish.jpg
    python veo.py "Smooth transition" --image start.jpg --last-frame end.jpg
    python veo.py "The cat plays with the yarn" --reference cat.png --reference yarn.png
    python veo.py "Continue the scene" --video clip.mp4
"""

import argparse
import os
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import client as gc  # noqa: E402
from lib import media, output  # noqa: E402

DEFAULT_MODEL = os.getenv("GEMINI_VEO_MODEL", "veo-3.1-generate-preview")
FAST_MODEL = "veo-3.1-fast-generate-preview"
LITE_MODEL = "veo-3.1-lite-generate-preview"

VEO_SUNSET = date(2026, 10, 22)

RESOLUTIONS = ["720p", "1080p", "4k"]
ASPECT_RATIOS = ["16:9", "9:16"]
DURATIONS = ["4", "6", "8"]
MAX_REFERENCES = 3
POLL_SECONDS = 10


def check_sunset():
    """Refuse after the shutdown date; warn before it."""
    days_left = (VEO_SUNSET - date.today()).days
    if days_left < 0:
        gc.fail(f"Veo 3.1 was shut down on {VEO_SUNSET}. Use gemini:omni instead.")
    print(f"Note: Veo 3.1 shuts down on {VEO_SUNSET} ({days_left} days left). "
          "gemini:omni is the long-term path.")


def load_image(types, path, label):
    p = media.require_file(path, label)
    return types.Image(image_bytes=p.read_bytes(), mime_type=media.mime_type(p))


def generate_video(client, types, prompt, model, config, image=None, video=None):
    """Start a Veo operation and poll until it finishes. Returns the video or None."""
    label = {FAST_MODEL: "Veo 3.1 Fast", LITE_MODEL: "Veo 3.1 Lite"}.get(model, "Veo 3.1")
    print(f"Generating video with {label} ({model})...")
    print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print()
    try:
        kwargs = {"model": model, "prompt": prompt, "config": config}
        if image is not None:
            kwargs["image"] = image
        if video is not None:
            kwargs["video"] = video
        operation = client.models.generate_videos(**kwargs)
        while not operation.done:
            print("Rendering video...")
            time.sleep(POLL_SECONDS)
            operation = client.operations.get(operation)
    except Exception as e:
        return gc.explain_error(
            e, model,
            fallback_hint="Veo 3.1 shuts down on 2026-10-22; try gemini:omni",
        )

    if getattr(operation, "error", None):
        gc.fail(f"Veo returned an error: {operation.error}")
    response = getattr(operation, "response", None)
    videos = getattr(response, "generated_videos", None) or []
    if not videos:
        gc.fail("No video in API response.",
                ["The model may have refused the request (safety filter)."])
    return videos[0].video


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate cinematic video clips with Veo 3.1.")
    parser.add_argument("prompt", nargs="+", help="What the video should show.")
    parser.add_argument("--fast", action="store_true",
                        help=f"Use the faster, cheaper model ({FAST_MODEL}).")
    parser.add_argument("--lite", action="store_true",
                        help=f"Use the cheapest model ({LITE_MODEL}). No 4k.")
    parser.add_argument("--model", default=None,
                        help=f"Explicit model ID (overrides --fast/--lite). Default: {DEFAULT_MODEL}.")
    parser.add_argument("--image", metavar="PATH", help="Start frame for image-to-video.")
    parser.add_argument("--last-frame", metavar="PATH", help="End frame. Needs --image.")
    parser.add_argument("--reference", action="append", metavar="PATH",
                        help=f"Subject reference image, up to {MAX_REFERENCES}. Forces 8 s.")
    parser.add_argument("--video", metavar="PATH",
                        help="Veo-generated clip to extend by 7 s (720p only).")
    parser.add_argument("--duration", choices=DURATIONS, default=None,
                        help="Clip length in seconds. 1080p, 4k, and references need 8.")
    parser.add_argument("--resolution", choices=RESOLUTIONS, help="Default 720p.")
    parser.add_argument("--aspect-ratio", choices=ASPECT_RATIOS, help="16:9 (default) or 9:16.")
    parser.add_argument("--negative-prompt", help="What to keep out of the video.")
    parser.add_argument("--output-dir", default=".",
                        help="Directory to save the video (default: current directory).")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    check_sunset()

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        gc.fail("Prompt cannot be empty.")
    if args.last_frame and not args.image:
        gc.fail("--last-frame needs --image for the start frame.")
    if sum(map(bool, [args.image, args.reference, args.video])) > 1:
        gc.fail("Choose one of --image, --reference, or --video per run.")

    model = args.model or (LITE_MODEL if args.lite else FAST_MODEL if args.fast else DEFAULT_MODEL)
    if model == LITE_MODEL and args.resolution == "4k":
        gc.fail("Veo 3.1 Lite has no 4k output. Use 720p or 1080p.")

    duration = args.duration
    if args.reference or args.resolution in ("1080p", "4k"):
        if duration and duration != "8":
            gc.fail("Reference images, 1080p, and 4k need --duration 8.")
        duration = "8"

    client = gc.get_client()
    _, types = gc.genai_modules()

    config_kwargs = {}
    if duration:
        config_kwargs["duration_seconds"] = int(duration)
    if args.resolution:
        config_kwargs["resolution"] = args.resolution
    if args.aspect_ratio:
        config_kwargs["aspect_ratio"] = args.aspect_ratio
    if args.negative_prompt:
        config_kwargs["negative_prompt"] = args.negative_prompt
    if args.last_frame:
        config_kwargs["last_frame"] = load_image(types, args.last_frame, "Last frame")
    if args.reference:
        if len(args.reference) > MAX_REFERENCES:
            gc.fail(f"Too many reference images: {len(args.reference)} given, {MAX_REFERENCES} allowed.")
        config_kwargs["reference_images"] = [
            types.VideoGenerationReferenceImage(
                image=load_image(types, p, "Reference image"), reference_type="asset")
            for p in args.reference
        ]

    image = load_image(types, args.image, "Start frame") if args.image else None
    video = None
    if args.video:
        p = media.require_file(args.video, "Video")
        video = types.Video(video_bytes=p.read_bytes(), mime_type="video/mp4")
        config_kwargs.setdefault("resolution", "720p")

    result = generate_video(
        client, types, prompt, model,
        types.GenerateVideosConfig(**config_kwargs), image=image, video=video,
    )
    if result is None:
        sys.exit(1)

    path = output.output_path("veo", "mp4", args.output_dir)
    try:
        client.files.download(file=result, destination=str(path))
    except Exception as e:
        gc.fail(f"Failed to download the video: {e}")
    print(f"\nSaved to: {path.absolute()}")
    print("\n✓ Video generation complete!")
    print(f"✓ Saved as: {path.name}")


if __name__ == "__main__":
    main()

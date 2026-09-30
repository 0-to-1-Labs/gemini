#!/usr/bin/env python3
"""
Gemini Omni video generator (gemini:omni)
Generates, edits, and extends short videos with native audio via the
Interactions API.

Usage:
    python omni.py "A marble rolling down a chain-reaction track, one smooth shot"
    python omni.py "Turn this into realistic footage of the fish swimming" --image fish.jpg
    python omni.py "A smooth cinematic transition" --image start.jpg --last-frame end.jpg
    python omni.py "<IMAGE_REF_0> bats at <IMAGE_REF_1>" --reference cat.png --reference yarn.png
    python omni.py "Continue the scene" --video clip.mp4
    python omni.py "Make the violin invisible" --continue <interaction-id>
"""

import argparse
import base64
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import client as gc  # noqa: E402
from lib import media, output  # noqa: E402

# Gemini Omni Flash (GA). Override with --model or GEMINI_OMNI_MODEL.
DEFAULT_MODEL = os.getenv("GEMINI_OMNI_MODEL", "gemini-omni-1.1-flash")

RESOLUTIONS = ["360p", "720p", "1080p", "4k"]
ASPECT_RATIOS = ["16:9", "9:16"]
MAX_REFERENCES = 3
POLL_SECONDS = 5


def file_id_from_uri(uri):
    """Extract the Files API id from a download URI."""
    match = re.search(r"files/([A-Za-z0-9_-]+)", uri or "")
    if not match:
        gc.fail(f"Could not parse a file id from the video URI: {uri}")
    return match.group(1)


def wait_for_video(client, video_output):
    """Poll the Files API until a URI-delivered video is ready."""
    file_id = file_id_from_uri(video_output.uri)
    while True:
        try:
            info = client.files.get(name=f"files/{file_id}")
        except Exception as e:
            gc.fail(f"Could not check the video file status: {e}",
                    [f"Video URI: {video_output.uri}"])
        state = info.state.name if info.state else "UNKNOWN"
        if state == "ACTIVE":
            return info
        if state == "FAILED":
            gc.fail("Video generation failed on Google's side.")
        print("Rendering video...")
        time.sleep(POLL_SECONDS)


def generate_video(client, prompt, model, task, parts, resolution=None,
                   aspect_ratio=None, previous_id=None):
    """Run one Omni interaction. Returns the interaction, or None on failure."""
    print(f"Generating video with Gemini Omni ({model}), task={task}...")
    print(f"Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    if resolution or aspect_ratio:
        print(f"Output: resolution={resolution or 'default'}, "
              f"aspect_ratio={aspect_ratio or 'default'}")
    if previous_id:
        print(f"Editing interaction: {previous_id}")
    print()

    response_format = {"type": "video", "delivery": "uri"}
    if resolution:
        response_format["resolution"] = resolution
    if aspect_ratio:
        response_format["aspect_ratio"] = aspect_ratio

    contents = [*parts, {"type": "text", "text": prompt}]
    kwargs = {
        "model": model,
        "input": contents,
        "response_format": response_format,
        "generation_config": {"video_config": {"task": task}},
    }
    if previous_id:
        kwargs["previous_interaction_id"] = previous_id

    try:
        return client.interactions.create(**kwargs)
    except Exception as e:
        return gc.explain_error(
            e, model,
            fallback_hint="Check the models page for the current Omni model IDs",
        )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate, edit, or extend short videos with Gemini Omni.",
    )
    parser.add_argument("prompt", nargs="+", help="What the video should show.")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Model ID. Default: {DEFAULT_MODEL}.")
    parser.add_argument("--image", metavar="PATH",
                        help="Start frame for image-to-video.")
    parser.add_argument("--last-frame", metavar="PATH",
                        help="End frame. Needs --image. The model animates between them.")
    parser.add_argument("--reference", action="append", metavar="PATH",
                        help=f"Subject reference image, up to {MAX_REFERENCES}. "
                             "Refer to them in the prompt as <IMAGE_REF_0>, <IMAGE_REF_1>...")
    parser.add_argument("--video", metavar="PATH",
                        help="Existing clip (10 s or less) to extend by 3 to 10 s.")
    parser.add_argument("--continue", dest="previous_id", metavar="INTERACTION_ID",
                        help="Edit the video from an earlier run (id printed by that run).")
    parser.add_argument("--resolution", choices=RESOLUTIONS,
                        help="Output resolution. Default 720p. 1080p and 4k are upscaled.")
    parser.add_argument("--aspect-ratio", choices=ASPECT_RATIOS,
                        help="16:9 (default) or 9:16.")
    parser.add_argument("--output-dir", default=".",
                        help="Directory to save the video (default: current directory).")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    prompt = " ".join(args.prompt).strip()
    if not prompt:
        gc.fail("Prompt cannot be empty.")
    if args.last_frame and not args.image:
        gc.fail("--last-frame needs --image for the start frame.")
    modes = [bool(args.image), bool(args.reference), bool(args.video), bool(args.previous_id)]
    if sum(modes) > 1:
        gc.fail("Choose one of --image, --reference, --video, or --continue per run.")

    client = gc.get_client()

    parts = []
    if args.video:
        task = "extend"
        uploaded = media.upload(client, args.video)
        parts.append({"type": "video", "uri": uploaded.uri})
    elif args.previous_id:
        task = "edit"
    elif args.reference:
        task = "reference_to_video"
        parts.extend(media.image_parts(client, args.reference, MAX_REFERENCES, "Reference image"))
    elif args.image:
        task = "image_to_video"
        frames = [args.image] + ([args.last_frame] if args.last_frame else [])
        parts.extend(media.image_parts(client, frames, 2, "Frame image"))
    else:
        task = "text_to_video"

    interaction = generate_video(
        client, prompt, args.model, task, parts,
        resolution=args.resolution, aspect_ratio=args.aspect_ratio,
        previous_id=args.previous_id,
    )
    if interaction is None:
        sys.exit(1)

    text = gc.output_text(interaction)
    if text:
        print(f"Model response: {text}")

    print(f"Interaction id: {interaction.id}")
    video = getattr(interaction, "output_video", None)
    if video is None:
        gc.fail("No video in API response.",
                ["The model may have refused the request or returned text only."])

    path = output.output_path("omni", "mp4", args.output_dir)
    if getattr(video, "uri", None):
        print(f"Video URI: {video.uri}")
        wait_for_video(client, video)
        client.files.download(file=video.uri, destination=str(path))
        print(f"\nSaved to: {path.absolute()}")
    elif getattr(video, "data", None):
        path = output.save_bytes(base64.b64decode(video.data), "omni", "mp4", args.output_dir)
    else:
        gc.fail("Video response had neither a URI nor inline data.")

    print("\n✓ Video generation complete!")
    print(f"✓ Saved as: {path.name}")
    print(f"✓ Interaction id (for --continue edits): {interaction.id}")


if __name__ == "__main__":
    main()

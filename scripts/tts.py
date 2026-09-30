#!/usr/bin/env python3
"""
Gemini text-to-speech (gemini:tts)
Turns text into a WAV file with one voice, or a two-speaker dialogue.

Usage:
    python tts.py "Welcome to the show." --voice Kore --style "warm and upbeat"
    python tts.py --file script.txt --voice Puck
    python tts.py --file dialogue.txt --speaker Joe=Puck --speaker Jane=Kore

Dialogue files use one line per turn, "Name: text". Lines without a
"Name:" prefix belong to the previous speaker.
"""

import argparse
import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib import client as gc  # noqa: E402
from lib import output  # noqa: E402

DEFAULT_MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
LITE_MODEL = "gemini-3.8-flash-lite-tts"
DEFAULT_VOICE = "Kore"
MAX_SPEAKERS = 2

VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
]


def parse_dialogue(text, speakers):
    """Split 'Name: line' text into (speaker, text) turns."""
    turns = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        name, sep, rest = line.partition(":")
        if sep and name.strip() in speakers:
            turns.append([name.strip(), rest.strip()])
        elif turns:
            turns[-1][1] += " " + line
        else:
            gc.fail(f"Dialogue must start with a speaker line. Got: {line[:60]}")
    return turns


def build_request(text, style, speakers, voice):
    """Return (input, generation_config) for one or two speakers."""
    if speakers:
        turns = parse_dialogue(text, speakers)
        content = []
        for name, line in turns:
            annotation = {"type": "speech_metadata", "speaker": name}
            if style:
                annotation["style"] = style
            content.append({"type": "text", "text": line, "annotations": [annotation]})
        speech_config = {
            "mode": "conversational",
            "speakers": [{"speaker": n, "voice": v} for n, v in speakers.items()],
        }
    else:
        item = {"type": "text", "text": text}
        if style:
            item["annotations"] = [{"type": "speech_metadata", "style": style}]
        content = [item]
        speech_config = [{"voice": voice}]
    return [{"type": "user_input", "content": content}], {"speech_config": speech_config}


def synthesize(client, model, request_input, generation_config):
    try:
        return client.interactions.create(
            model=model,
            input=request_input,
            response_format={"type": "audio"},
            generation_config=generation_config,
        )
    except Exception as e:
        return gc.explain_error(e, model, fallback_hint="Try the default Flash TTS model")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Text to speech with Gemini TTS.")
    parser.add_argument("text", nargs="*", help="Text to speak (or use --file).")
    parser.add_argument("--file", metavar="PATH", help="Read the text or dialogue from a file.")
    parser.add_argument("--voice", default=DEFAULT_VOICE,
                        help=f"Voice name for single-speaker output. Default: {DEFAULT_VOICE}.")
    parser.add_argument("--style", help="Delivery style, e.g. 'calm and slow', 'excited'.")
    parser.add_argument("--speaker", action="append", metavar="NAME=VOICE",
                        help=f"Dialogue speaker mapping, up to {MAX_SPEAKERS}. Repeatable.")
    parser.add_argument("--lite", action="store_true", help=f"Use {LITE_MODEL}.")
    parser.add_argument("--model", default=None, help=f"Model ID. Default: {DEFAULT_MODEL}.")
    parser.add_argument("--list-voices", action="store_true", help="Print the prebuilt voices.")
    parser.add_argument("--output-dir", default=".",
                        help="Directory to save the audio (default: current directory).")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    if args.list_voices:
        print("\n".join(VOICES))
        return

    if args.file:
        text = Path(args.file).expanduser().read_text(encoding="utf-8")
    else:
        text = " ".join(args.text)
    text = text.strip()
    if not text:
        gc.fail("Nothing to speak. Pass text or --file.")

    speakers = {}
    for item in args.speaker or []:
        name, sep, voice = item.partition("=")
        if not sep or not name or not voice:
            gc.fail(f"Bad --speaker value '{item}'. Use NAME=VOICE, e.g. Joe=Puck.")
        speakers[name.strip()] = voice.strip()
    if len(speakers) > MAX_SPEAKERS:
        gc.fail(f"Gemini TTS supports {MAX_SPEAKERS} speakers per request.")

    model = args.model or (LITE_MODEL if args.lite else DEFAULT_MODEL)
    request_input, generation_config = build_request(text, args.style, speakers, args.voice)

    print(f"Synthesizing with Gemini TTS ({model})...")
    print(f"Voices: {', '.join(f'{n}={v}' for n, v in speakers.items()) or args.voice}")
    print(f"Text: {text[:100]}{'...' if len(text) > 100 else ''}")
    print()

    client = gc.get_client()
    interaction = synthesize(client, model, request_input, generation_config)
    if interaction is None:
        sys.exit(1)

    audio = getattr(interaction, "output_audio", None)
    if audio is None or not getattr(audio, "data", None):
        gc.fail("No audio in API response.")

    ext = output.ext_for_mime(getattr(audio, "mime_type", None), "wav")
    path = output.save_bytes(base64.b64decode(audio.data), "tts", ext, args.output_dir)
    print("\n✓ Speech generation complete!")
    print(f"✓ Saved as: {path.name}")


if __name__ == "__main__":
    main()

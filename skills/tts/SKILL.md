---
name: tts
description: Convert text to natural speech audio (WAV) with Gemini TTS, using one of 30 voices or a two-speaker dialogue, with style directions like "calm" or "excited". Use when users ask to read text aloud, make a voiceover, narration, audiobook clip, podcast intro, or spoken dialogue. Free tier available.
license: MIT
metadata:
  author: sasser
  version: 2.0.0
allowed-tools: Bash
argument-hint: [text or --file script.txt] [--voice Kore] [--style "warm"] [--speaker Joe=Puck]
---

# Gemini Text-to-Speech

`gemini-3.8-flash-tts` speaks text in 130+ languages with 30 prebuilt voices.
Output is a 24 kHz mono WAV.

## Workflow

### Step 1: Pick the mode

- **One voice**: pass the text (or `--file`) and `--voice`.
- **Dialogue** (2 speakers max): write a file with one turn per line as
  `Name: text`, then map each name with `--speaker Name=Voice`.

### Step 2: Pick voices

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tts.py" --list-voices` for the full
list. Common picks:

| Voice | Character |
|---|---|
| Kore | firm, clear (default) |
| Puck | upbeat, youthful |
| Charon | deep, informative |
| Zephyr | bright |
| Aoede | breezy |
| Fenrir | excitable |
| Leda | youthful |
| Orus | firm, corporate |

### Step 3: Direct the delivery

- `--style "warm and slow"` sets the whole turn's delivery.
- Inline tags such as `<sigh>`, `<laugh>`, or `<pause>` mark moments in the text.
- Write numbers and abbreviations as the words the user wants spoken.

### Step 4: Run the script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tts.py" "TEXT" --voice Kore --style "STYLE"
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/tts.py" --file dialogue.txt --speaker Joe=Puck --speaker Jane=Kore
```

Flags:

- `--lite` — `gemini-3.8-flash-lite-tts`, cheaper, 100+ languages.
- `--output-dir <dir>`
- `--model <id>` — the `GEMINI_TTS_MODEL` environment variable changes the default.

Output is `tts_<timestamp>.wav`. Long scripts: split at natural breaks into
several runs, then tell the user how to join them (for example with `ffmpeg`).

## Cost

$9 per 1M audio output tokens for Flash (about $0.05 per minute of speech),
$6 for Lite. Both have a free tier. Prices double after 2026-12-31.

## Setup

`GEMINI_API_KEY` must be set (get one at https://aistudio.google.com/apikey).
Python 3.10+. The script auto-installs `google-genai` on first run.

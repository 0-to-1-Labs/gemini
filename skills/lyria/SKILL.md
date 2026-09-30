---
name: lyria
description: Compose a full song with vocals and lyrics, or an instrumental track, from a text description using Lyria 3.5. Outputs MP3 or WAV and prints the lyrics. Use when users ask for music, a song, a jingle, a soundtrack, a beat, background music, or a theme tune.
license: MIT
metadata:
  author: sasser
  version: 2.0.0
allowed-tools: Bash
argument-hint: [song description] [--wav] [--image mood.jpg]
---

# Lyria Music Generation

Lyria 3.5 (`lyria-3.5`) writes and performs a complete song from one prompt.
The prompt controls genre, mood, tempo, instruments, vocals, lyrics, structure,
and length.

## Workflow

### Step 1: Build the prompt

Cover, in plain sentences:

- **Genre and mood**: "upbeat indie pop", "dark cinematic orchestral".
- **Tempo and key** when the user cares: "120 BPM", "in D minor".
- **Instruments and vocals**: "female lead vocal, acoustic guitar, brushed drums".
  Say "instrumental" for no vocals.
- **Length**: "about 30 seconds" or "a two minute song". Default is a full song.
- **Lyrics**: give exact lyrics when the user has them, or a theme when not.
  Use `[Verse]`, `[Chorus]`, `[Bridge]` tags to set structure.

### Step 2: Run the script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lyria.py" "PROMPT" [flags]
```

Flags:

- `--wav` — WAV output instead of MP3. Use for editing or mastering.
- `--image <path>` — mood reference image, up to 10. The song matches the image.
- `--output-dir <dir>`
- `--model <id>` — `lyria-3-clip-preview` gives 30 second clips at half price.
  The `GEMINI_LYRIA_MODEL` environment variable changes the default.

Output is `lyria_<timestamp>.mp3` (44.1 kHz stereo). The script prints the
lyrics the model sang. There is no multi-turn editing; a change means a new
run with a revised prompt.

### Step 3: Report

Give the file path and the lyrics. All output carries a SynthID watermark.

## Cost

$0.08 per song. $0.04 per 30 second clip. There is no free tier.

## Examples

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lyria.py" "A warm lo-fi hip hop track, instrumental, vinyl crackle, soft Rhodes piano, 85 BPM, about one minute"

python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lyria.py" "An anthemic pop-rock song about finishing a marathon. Female lead vocal. [Verse] Mile twenty-six, legs of stone [Chorus] I'm still running, I'm not alone" --wav
```

## Setup

`GEMINI_API_KEY` must be set (get one at https://aistudio.google.com/apikey).
Python 3.10+. The script auto-installs `google-genai` on first run.

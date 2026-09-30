---
name: understand
description: Analyze, summarize, transcribe, or answer questions about video, audio, images, PDFs, and public YouTube links using Gemini. Use when a user points at a media file or YouTube URL that Claude cannot read directly, asks for a transcript, meeting notes, a video summary, or what a recording or document says.
license: MIT
metadata:
  author: sasser
  version: 2.0.0
allowed-tools: Bash
argument-hint: [question] --file recording.mp4 | --url https://youtube.com/watch?v=...
---

# Gemini Media Understanding

Gemini reads media that Claude Code cannot open on its own: video, audio, PDFs,
and YouTube videos. Ask it a question and get text back.

## Workflow

### Step 1: Match the input

| Input | Flag | Notes |
|---|---|---|
| Local video (mp4, mov, webm, mkv) | `--file` | Up to 1 hour at high detail, 3 hours at low. Sampled at 1 fps. |
| Local audio (mp3, wav, m4a, flac, ogg) | `--file` | Up to 9.5 hours. |
| PDF | `--file` | Up to 1,000 pages or 50 MB. |
| Image | `--file` | Any common format. |
| YouTube | `--url` | Public videos only. Up to 10 per run. |

Files over 20 MB upload through the Files API automatically. Google keeps
uploads for 48 hours.

### Step 2: Write the prompt

Ask for the output shape you want: "five bullets", "a table of action items
with owners and timestamps", "quote the exact clause". For long videos, name
the section: `--start 1200 --end 1500` (seconds) and `--fps 0.5` cut tokens.

### Step 3: Run the script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/understand.py" "QUESTION" --file recording.mp4
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/understand.py" "Summarize in five bullets" --url "https://www.youtube.com/watch?v=..."
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/understand.py" --transcribe --file interview.m4a --out transcript.md
```

Flags:

- `--transcribe` — switches to `gemini-3.5-transcribe` with a verbatim
  transcription prompt. Add your own prompt to change the format.
- `--out <path>` — also write the answer to a file. Use it for transcripts.
- `--fps`, `--start`, `--end` — video sampling and clipping.
- `--model <id>` — default `gemini-3.8-flash`. Use `gemini-3.1-pro-preview`
  for hard reasoning over long documents. The `GEMINI_UNDERSTAND_MODEL`
  environment variable changes the default.

### Step 4: Use the answer

The script prints the answer to stdout. Read it and continue the user's task.
Quote Gemini's answer as Gemini's, not as something you verified yourself.

## Cost

Token rates. Video costs about 100 tokens per second at low resolution, audio
32 tokens per second, PDF 258 tokens per page. A 10 minute video is about
60K tokens, under $0.05 on Flash. Transcription is about $0.003 per minute.
Flash has a free tier (8 hours of YouTube per day).

## Setup

`GEMINI_API_KEY` must be set (get one at https://aistudio.google.com/apikey).
Python 3.10+. The script auto-installs `google-genai` on first run.

---
name: veo
description: Generate 4, 6, or 8 second cinematic video clips with sound using Veo 3.1 (standard, Fast, or Lite). Supports image-to-video, first-and-last-frame, reference images, and 7-second extensions. Use only when the user names Veo explicitly. Veo 3.1 shuts down on 2026-10-22; gemini:omni is the default video skill.
license: MIT
metadata:
  author: sasser
  version: 2.0.0
allowed-tools: Bash
argument-hint: [video description] [--fast|--lite] [--duration 8] [--resolution 1080p]
---

# Veo 3.1 Video Generation (time-limited)

Google retires every Veo 3.1 model on **2026-10-22**. The script refuses to run
after that date and points to `gemini:omni`. Before that date it prints the days
left. Use this skill only when the user asks for Veo by name.

## Workflow

### Step 1: Pick the model

- Default `veo-3.1-generate-preview`: best quality. $0.40 per second.
- `--fast`: `veo-3.1-fast-generate-preview`. $0.10 per second at 720p.
- `--lite`: `veo-3.1-lite-generate-preview`. $0.05 per second. No 4k.

### Step 2: Pick the task

| User has | Flags |
|---|---|
| A description only | none |
| One image to animate | `--image start.jpg` |
| A start and an end image | `--image start.jpg --last-frame end.jpg` |
| Subjects that must stay consistent | `--reference a.png --reference b.png` (max 3, forces 8 s) |
| A Veo clip to extend by 7 s | `--video clip.mp4` (720p only) |

### Step 3: Write the prompt

Describe one shot: subject, action, camera move, setting, light, and sound.
Dialogue goes in quotes. Put unwanted elements in `--negative-prompt`, not in
the prompt.

### Step 4: Run the script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/veo.py" "PROMPT" [flags]
```

Flags:

- `--duration 4|6|8` — 1080p, 4k, and reference images require 8.
- `--resolution 720p|1080p|4k` — default 720p.
- `--aspect-ratio 16:9|9:16`
- `--negative-prompt "text"`
- `--output-dir <dir>`
- `--model <id>` — the `GEMINI_VEO_MODEL` environment variable changes the default.

The script polls every 10 seconds. Rendering takes between 11 seconds and 6
minutes. Output is `veo_<timestamp>.mp4`. Google deletes the server copy after
2 days, so the local file is the only copy.

## Cost

State the estimate before the run: seconds × rate. An 8 second standard clip
at 1080p is $3.20. The same clip on Lite is $0.64. There is no free tier.

## Setup

`GEMINI_API_KEY` must be set (get one at https://aistudio.google.com/apikey).
Python 3.10+. The script auto-installs `google-genai` on first run.

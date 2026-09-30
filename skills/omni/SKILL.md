---
name: omni
description: Generate, edit, or extend short videos (3 to 10 seconds, with sound) using Gemini Omni Flash. Supports text-to-video, image-to-video, first-and-last-frame animation, subject reference images, conversational edits, and extending a clip. Use when users ask for a video, animation, clip, motion, b-roll, or to animate an image. For still images use gemini:nanobanana.
license: MIT
metadata:
  author: sasser
  version: 2.0.0
allowed-tools: Bash
argument-hint: [video description] [--image start.jpg] [--resolution 720p] [--aspect-ratio 9:16]
---

# Gemini Omni Video Generation

Omni Flash (`gemini-omni-1.1-flash`) turns a prompt into a 3 to 10 second MP4
with native audio. It is Google's long-term video model. Veo 3.1 shuts down on
2026-10-22; prefer this skill unless the user names Veo.

## Workflow

### Step 1: Pick the task from the request

| User has | Task | Flags |
|---|---|---|
| A description only | text-to-video | none |
| One image to animate | image-to-video | `--image start.jpg` |
| A start and an end image | frame interpolation | `--image start.jpg --last-frame end.jpg` |
| Subjects that must stay consistent | reference-to-video | `--reference cat.png --reference yarn.png` (max 3) |
| A clip to make longer | extend | `--video clip.mp4` (input 10 s or less, adds 3 to 10 s) |
| A video from an earlier run to change | edit | `--continue <interaction-id>` |

Use one task per run. Reference images are named in the prompt as
`<IMAGE_REF_0>`, `<IMAGE_REF_1>`, in the order given.

### Step 2: Write the prompt

Write one continuous shot in plain sentences. Cover:

- **Subject and action**: who or what moves, and how.
- **Camera**: "slow dolly in", "static wide shot", "handheld follow".
- **Setting and light**: place, time of day, weather, light source.
- **Sound**: ambient noise, dialogue in quotes, music mood. Omni renders audio.
- **Length**: say "3 seconds" or "8 seconds" in the prompt. There is no duration flag.

Do not use negative prompts, system instructions, or keyword lists. The model
ignores them.

### Step 3: Run the script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/omni.py" "PROMPT" [flags]
```

Flags:

- `--resolution 360p|720p|1080p|4k` — default 720p. 1080p and 4k are upscales
  of 720p; use them only when asked. Use 360p for cheap drafts.
- `--aspect-ratio 16:9|9:16` — 9:16 for phones, stories, reels.
- `--output-dir <dir>` — default is the current directory.
- `--model <id>` — another Omni model when the user names one. The
  `GEMINI_OMNI_MODEL` environment variable changes the default.

The script uploads inputs, waits for rendering (usually under two minutes),
saves `omni_<timestamp>.mp4`, and prints the interaction id. Keep that id in
the conversation so the user can ask for edits with `--continue`.

### Step 4: Report

Tell the user the file path and the interaction id. Offer one edit or extension
if the result is close.

## Cost

About $0.10 per second of 720p video, so a 5 second clip is about $0.50.
There is no free tier. Say the estimate before a run longer than 5 seconds,
at 1080p or 4k, or when the user asks for several variants.

## Examples

```bash
# Text to video, vertical
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/omni.py" "A barista pours latte art in a sunlit cafe, slow overhead shot, soft jazz, 5 seconds" --aspect-ratio 9:16

# Animate a product photo
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/omni.py" "The camera orbits the bottle slowly, condensation glistens, 4 seconds" --image bottle.jpg

# Keep two subjects consistent
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/omni.py" "<IMAGE_REF_0> chases <IMAGE_REF_1> across a lawn, 6 seconds" --reference dog.png --reference ball.png

# Edit the last result
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/omni.py" "Make it night with warm street lights" --continue v1_abc123
```

## Setup

`GEMINI_API_KEY` must be set (get one at https://aistudio.google.com/apikey).
Python 3.10+. The script auto-installs `google-genai` on first run.

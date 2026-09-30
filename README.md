<p align="center">
  <img src="banner.png" alt="Gemini plugin" width="600">
</p>

# Gemini

A Claude Code plugin for Google's Gemini media services. One API key, one
skill per service:

| Skill | What it does | Model |
|---|---|---|
| `gemini:nanobanana` | Generate and edit images with perfect text rendering | `gemini-3-pro-image`, `gemini-3.1-flash-image`, `gemini-3.1-flash-lite-image` |
| `gemini:omni` | Generate, edit, and extend 3 to 10 second videos with sound | `gemini-omni-1.1-flash` |
| `gemini:veo` | Cinematic 4 to 8 second clips (until 2026-10-22) | `veo-3.1-*-preview` |
| `gemini:lyria` | Compose full songs with lyrics, or instrumentals | `lyria-3.5` |
| `gemini:tts` | Text to speech, 30 voices, two-speaker dialogue | `gemini-3.8-flash-tts` |
| `gemini:understand` | Summarize, transcribe, or question video, audio, PDFs, YouTube | `gemini-3.8-flash`, `gemini-3.5-transcribe` |

Each skill teaches Claude how to prompt that model well, then runs a small
Python script that calls the Gemini API and saves the result next to your work.

## Install

```
/plugin marketplace add 0-to-1-Labs/claude-marketplace
/plugin install gemini@0-to-1-labs
```

Then set your API key:

1. Get one at [Google AI Studio](https://aistudio.google.com/apikey)
2. Add to your shell config:
   ```bash
   export GEMINI_API_KEY="your-key-here"
   ```
3. Restart Claude Code

Python 3.10 or later is required. On first run the scripts create a private
virtual environment at `~/.cache/claude-gemini-plugin/venv` (or under
`$CLAUDE_PLUGIN_DATA` when set) and install `google-genai` into it. They never
change your system or Homebrew Python.

## Keep the plugin updated

Claude Code can update this plugin automatically. Auto-update is off by default for third-party marketplaces, so turn it on once:

1. Run `/plugin`.
2. Open the **Marketplaces** tab and select `0-to-1-labs`.
3. Choose **Enable auto-update**.

Claude Code then checks for new versions after each session start and installs them. Restart Claude Code to load an update.

To update by hand:

```
claude plugin marketplace update 0-to-1-labs
claude plugin update gemini@0-to-1-labs
```

## Usage

Ask Claude Code in plain words. The right skill activates on its own, or name
it with a slash command.

**Images**
```
Generate a poster for a jazz night called "Blue Moon" on Friday
Take portrait.png and replace the background with a snowy mountain at golden hour
/gemini:nanobanana a 9:16 phone wallpaper of a rainy Tokyo street at night
```

**Video**
```
Make a 5 second clip of a barista pouring latte art, vertical
Animate bottle.jpg so the camera slowly orbits it
```

**Music and speech**
```
Write a 30 second ukulele jingle about our coffee shop
Read intro.txt aloud in a warm voice
Make dialogue.txt into a two-voice conversation
```

**Understanding**
```
Summarize meeting.mp4 in five bullets with action items
Transcribe interview.m4a to transcript.md
What does this YouTube video say about caching? https://www.youtube.com/watch?v=...
```

## Output files

Files save to the current directory (or `--output-dir`) as
`<skill>_YYYYMMDD_HHMMSS.<ext>`:

- `nanobanana_*.jpg` (add `--png` for PNG)
- `omni_*.mp4`, `veo_*.mp4`
- `lyria_*.mp3` (add `--wav` for WAV)
- `tts_*.wav`

All generated media carries an invisible
[SynthID](https://deepmind.google/technologies/synthid/) watermark.

## Cost

Image, video, and music models have no free tier. TTS and understanding do.
Typical prices (check [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing)):

| Skill | Price |
|---|---|
| Image | $0.03 (Lite) to $0.24 (Pro 4K) per image |
| Omni video | about $0.10 per second at 720p |
| Veo video | $0.05 to $0.60 per second by model and resolution |
| Music | $0.08 per song |
| Speech | about $0.05 per minute |
| Understanding | token rates; a 10 minute video is under $0.05 |

Each skill tells Claude to state the cost before an expensive run.

## Model overrides

Every script takes `--model <id>`. Environment variables change the defaults
without an edit: `GEMINI_OMNI_MODEL`, `GEMINI_VEO_MODEL`, `GEMINI_LYRIA_MODEL`,
`GEMINI_TTS_MODEL`, `GEMINI_UNDERSTAND_MODEL`.

## Veo sunset

Google shuts down all Veo 3.1 models on 2026-10-22 and names Omni as the
replacement. `gemini:veo` runs until then, prints the days left, and refuses
after. A later release removes it.

## Migrating from nanobanana

Version 2.0.0 renames the plugin from `nanobanana` to `gemini`.

- The skill `nanobanana:nanobanana` is now `gemini:nanobanana`. Its prompts,
  flags, and behavior are the same. New flags: `--lite`, `--thinking high`,
  `--png`.
- Images save as JPEG, the model's native format. The 1.x plugin re-encoded the
  same JPEG as PNG. Pass `--png` for that behavior.
- The marketplace maps the old name to the new one, and `/plugin` marks the
  old install as renamed. Finish the move by hand:
  ```
  /plugin marketplace update 0-to-1-labs
  /plugin install gemini@0-to-1-labs
  ```
  If `nanobanana@0-to-1-labs` still shows in `/plugin` afterwards, uninstall it.
- The standalone `install.sh` is gone. Use the marketplace.

## Troubleshooting

**"GEMINI_API_KEY not set"** — export it in your shell and restart Claude Code.
`GOOGLE_API_KEY` also works.

**"google-genai not installed" or too old** — the scripts need
`google-genai>=2.3.0`. Delete `~/.cache/claude-gemini-plugin/venv` and re-run;
the script rebuilds it.

**"incompatible architecture" on import** — a package was built for another
CPU. Delete `~/.cache/claude-gemini-plugin/venv` and re-run.

**API errors** — check the key at [Google AI Studio](https://aistudio.google.com/apikey).
Image, video, and music calls fail on a key without billing.

## Links

- [Gemini API docs](https://ai.google.dev/gemini-api/docs)
- [Image generation](https://ai.google.dev/gemini-api/docs/image-generation)
- [Omni video](https://ai.google.dev/gemini-api/docs/omni)
- [Veo](https://ai.google.dev/gemini-api/docs/veo)
- [Lyria](https://ai.google.dev/gemini-api/docs/music-generation)
- [Speech](https://ai.google.dev/gemini-api/docs/speech-generation)
- [Video understanding](https://ai.google.dev/gemini-api/docs/video-understanding)
- [Deprecations](https://ai.google.dev/gemini-api/docs/deprecations)

## License

MIT. Do whatever you want with it.

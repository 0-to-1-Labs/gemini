---
name: nanobanana
description: Generate or edit photorealistic images with perfect text rendering using Nano Banana Pro (Gemini 3 Pro Image) or Nano Banana 2. Automatically enhances prompts for this reasoning-based model and supports aspect ratio, resolution, and reference-image editing. Use when users ask to create or edit images, logos, infographics, posters, diagrams, wallpapers, or any still visual content. For video use gemini:omni.
license: MIT
metadata:
  author: sasser
  version: 2.1.0
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/scripts/nanobanana.py *)
argument-hint: [image description] [--aspect-ratio 16:9] [--resolution 2K] [--image ref.png]
---

# Nano Banana Pro Image Generation

This skill enables high-quality image generation using Nano Banana Pro via the Gemini API. It automatically transforms user requests into optimized prompts that exploit Nano Banana Pro's unique capabilities: perfect text rendering, complex reasoning for infographics, and photorealistic consistency.

## Core Philosophy

Nano Banana Pro is a **reasoning engine**, not just a pattern matcher. It requires clear, natural language directives describing the scene's logic, lighting, and exact textual content. Avoid "word salad" keywords like "4k, trending on artstation."

## Prompt Enhancement Workflow

When a user requests an image, follow these steps:

### Step 1: Analyze the Request

Identify which pattern applies:

- **Pattern A: Infographic** - User wants explanations, guides, data visualization, diagrams, or technical illustrations
- **Pattern B: Typographic** - User wants logos, posters, signage, t-shirts, or text-heavy designs
- **Pattern C: Character** - User describes specific people or characters with distinct features
- **General** - Standard scenes, photos, or artistic images

### Step 2: Build the Enhanced Prompt

Use this modular structure (plain text, no markdown):

**[Subject & Action] + [Context & Environment] + [Specific Text/Data] + [Style & Medium] + [Technical Parameters]**

#### Components:

**1. Subject & Action (The "Who" and "What")**
- Be highly descriptive
- Include logic checks (e.g., "The reflection in the mirror shows a different expression")
- Example: "A fluffy Calico cat sitting upright like a human" not "A cat"

**2. Specific Text & Data (The Superpower)**
- Nano Banana Pro creates flawless text - USE THIS
- Format: "Render the text 'EXACT TEXT' on [object]"
- Always enclose text to render in single quotes within the prompt
- Example: "A neon sign in the window reads 'OPEN 24 HOURS' in a flickering blue font"

**3. Context & Environment**
- Describe the setting, background, surrounding elements
- Include spatial relationships and scene composition

**4. Style & Medium**
- Photorealism: "Shot on 35mm lens, f/1.8 aperture, cinematic lighting, soft bokeh"
- Infographic/Diagram: "A logical cross-section diagram," "An isometric assembly guide," "A flat-design flowchart"
- Artistic: "Oil painting with thick impasto strokes," "Vector art, clean lines, flat colors"

**5. Technical Parameters**
- Lighting: "Golden hour," "Studio softbox," "Volumetric fog," "Rembrandt lighting"
- Composition: "Rule of thirds," "Low angle looking up," "Macro close-up"

### Step 3: Pattern-Specific Strategies

**Pattern A: Infographic (Reasoning Heavy)**
- Request "cutaway" or "exploded view" for technical explanations
- Add labels with arrows pointing to components
- Specify "clean vector art on white background" for clarity
- Ensure text labels are "legible and perfectly spelled"
- Example: "A precise technical cutaway illustration of an espresso machine. Labels with arrows point to the 'Boiler', 'Pump', and 'Group Head'. The style is clean vector art on a white background. Text labels are legible and perfectly spelled."

**Pattern B: Typographic (Text Heavy)**
- Focus on font weight, kerning, and integration
- Describe the texture (worn paper, metal, glass, etc.)
- Specify text hierarchy (large title, smaller subtitle)
- Example: "A vintage travel poster for 'MARS'. The word 'MARS' is written in large, retro-futuristic bold red letters at the top. The bottom text reads 'Visit the Red Planet' in a smaller sans-serif font. The texture looks like worn paper."

**Pattern C: Character Consistency**
- Over-describe facial features for stability
- Include specific details: freckles, eye color, hair texture, distinctive features
- Specify exact pose and expression
- Example: "Close up portrait of a woman with distinct freckles and green eyes, wearing a silver headset. She is looking directly at the camera. Professional corporate photography, studio lighting."

### Step 4: Best Practices

**DO:**
- Use natural language with complete, descriptive sentences
- Request complex interactions that require understanding
- Adapt composition to format (vertical for mobile wallpapers, wide for banners)
- Specify exact text content in single quotes

**DON'T:**
- Use negative prompts or "anti-blur" keywords (bad hands, extra fingers, ugly)
- Use "glitch tokens" from Stable Diffusion
- Be vague or use generic descriptions

### Step 5: Generate the Image

After creating the enhanced prompt, write it to a file with the Write tool
(use your scratchpad directory, or another temporary directory), then pass
that file to the script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/nanobanana.py --prompt-file /path/to/prompt.txt
```

Never put the prompt text inside double quotes on the command line. The shell
expands `$`, backticks, and backslashes there, so a price like `$5` or a code
snippet in the prompt is changed or run before the script sees it. If you
cannot write a file, pipe the prompt through a quoted heredoc instead:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/nanobanana.py - --aspect-ratio 16:9 <<'PROMPT'
ENHANCED PROMPT HERE
PROMPT
```

The script will:
1. Check that the GEMINI_API_KEY environment variable exists
2. On first run, create a private virtual environment under
   `~/.cache/claude-gemini-plugin/venv` and install `google-genai` into it
   (it never changes the system Python; this prints one line and takes a
   moment)
3. Call the Gemini Interactions API with the enhanced prompt
4. Save every generated image (JPEG) to the current directory
5. Print the path of each saved image

Cost: about $0.13 per Pro image at 1K or 2K, $0.24 at 4K. Flash is $0.07 at 1K,
Lite is $0.03. There is no free tier for image models. Mention the price when a
user asks for many images or 4K.

#### Optional flags

Use these when the request implies a specific framing, quality, or an edit of an
existing image:

- `--aspect-ratio <ratio>` — choose framing instead of relying on the prompt
  alone. Supported: `1:1 2:3 3:2 3:4 4:3 4:5 5:4 9:16 16:9 21:9 1:4 4:1 1:8 8:1`.
  Pick `9:16` for phone wallpapers/stories, `16:9` or `21:9` for banners/wide
  shots, `1:1` for avatars/icons, `4:5` for portrait social posts, `4:1` or
  `8:1` for skinny web banners and `1:4` or `1:8` for tall side banners.
- `--resolution <512|1K|2K|4K>` — output resolution. Default is `1K`. Use
  `2K`/`4K` for posters, print, or detailed infographics with fine text.
  `512` works only with `--fast`; Lite is `1K` only.
- `--image <path>` — provide a reference/input image to **edit or combine**.
  Repeatable: pass `--image` multiple times to merge subjects, keep a character
  consistent, or transfer a style. The prompt then describes the desired change.
- `--fast` — use the faster, cheaper Flash model (Nano Banana 2) for quick
  drafts/iteration. Default (omit it) uses Nano Banana Pro for best text and
  fidelity.
- `--lite` — use the cheapest Lite model. 1K only. Good for icons and thumbnails.
- `--thinking high` — Flash models only. Use for complex scenes with many
  elements or tricky spatial logic.
- `--png` — re-encode the output as PNG for tools that require `.png`. The
  model itself emits JPEG.
- `--output-dir <dir>` — save somewhere other than the current directory.
- `--model <id>` — explicit model ID when the user names one.

**Examples:**

```bash
# A 9:16 phone wallpaper at 2K (prompt written to prompt.txt first)
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/nanobanana.py --prompt-file prompt.txt --aspect-ratio 9:16 --resolution 2K

# Edit an existing photo; prompt.txt says what to change, e.g. "Replace the
# background with a snowy mountain range at golden hour, keep the subject unchanged"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/nanobanana.py --prompt-file prompt.txt --image portrait.png

# Combine two reference images; prompt.txt says how, e.g. "Put the product from
# the first image onto the marble countertop from the second image, studio lighting"
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/nanobanana.py --prompt-file prompt.txt --image product.png --image kitchen.png
```

## Examples

**User Request:** "Make a cool poster for a jazz night called 'Blue Moon' happening on Friday."

**Enhanced Prompt:**
"A moody, atmospheric jazz club poster. In the center, a silhouette of a saxophone player is backlit by a large, glowing blue moon. The text 'BLUE MOON' is rendered in a stylish, Art Deco font at the top. Below the player, the text 'Friday Night Jazz' appears in a smaller, elegant serif font. The color palette is deep indigo, black, and silver. Texture of grainy cardstock."

---

**User Request:** "Show me a diagram of a plant cell."

**Enhanced Prompt:**
"A detailed, educational cross-section illustration of a plant cell. The image clearly shows and labels the 'Nucleus', 'Chloroplast', 'Vacuole', and 'Cell Wall'. The style is clean, 3D educational render with bright, distinct colors for each organelle. Background is clean white for readability."

---

**User Request:** "A photo of a cyberpunk street."

**Enhanced Prompt:**
"A hyper-realistic wide shot of a rainy cyberpunk street in Tokyo at night. Neon signs reflect in the puddles. One prominent holographic sign in the foreground reads 'CYBER NOODLES' in bright pink katakana and English. Steam rises from street vents. Cinematic lighting, high contrast."

## Setup Requirements

1. Set the GEMINI_API_KEY environment variable:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```
   Get a key at https://aistudio.google.com/apikey

2. Python 3.10 or later is required. On first run the script creates a
   private virtual environment at `~/.cache/claude-gemini-plugin/venv` (or
   under `$CLAUDE_PLUGIN_DATA` when that variable is set) and installs
   `google-genai` there (`pillow` too, only for `--png`). It never installs
   into the system or Homebrew Python. To rebuild the environment, delete
   that directory and run the script again.

## Error Handling

The script handles common errors:
- Missing GEMINI_API_KEY (exits with clear message, before any install)
- API failures (network issues, invalid requests)
- Responses with no image (prints the interaction status and API errors)
- File write permissions

All errors include helpful messages for troubleshooting.

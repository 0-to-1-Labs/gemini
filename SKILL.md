---
name: nanobanana
description: Generate or edit photorealistic images with perfect text rendering using Nano Banana Pro (Gemini 3 Pro Image). Automatically enhances prompts for this reasoning-based model and supports aspect ratio, resolution, and reference-image editing. Use when users ask to create or edit images, logos, infographics, posters, diagrams, wallpapers, or any visual content.
license: MIT
metadata:
  author: sasser
  version: 1.0.0
allowed-tools: Bash
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

After creating the enhanced prompt, generate the image using:

```bash
python "$CLAUDE_PLUGIN_ROOT/scripts/generate.py" "ENHANCED_PROMPT_HERE"
```

If `$CLAUDE_PLUGIN_ROOT` is not set (standalone skill install), use the absolute path:

```bash
python ~/.claude/skills/nanobanana/scripts/generate.py "ENHANCED_PROMPT_HERE"
```

Gemini is the default provider. When the user has configured
`ATLASCLOUD_API_KEY` (or `ATLAS_CLOUD_API_KEY`), text-to-image requests can opt
into Atlas Cloud:

```bash
python "$CLAUDE_PLUGIN_ROOT/scripts/generate.py" "ENHANCED_PROMPT_HERE" --provider atlas
```

The script will:
1. Validate the selected provider's API key (auto-installing the `google-genai`
   dependency on first Gemini use if needed)
2. Call the selected image API with the enhanced prompt
3. Save the generated image to the current directory
4. Print the filename of the saved image

#### Optional flags

Use these when the request implies a specific framing, quality, or an edit of an
existing image:

- `--aspect-ratio <ratio>` — choose framing instead of relying on the prompt
  alone. Supported: `1:1 2:3 3:2 3:4 4:3 4:5 5:4 9:16 16:9 21:9`.
  Pick `9:16` for phone wallpapers/stories, `16:9` or `21:9` for banners/wide
  shots, `1:1` for avatars/icons, `4:5` for portrait social posts.
- `--resolution <1K|2K|4K>` — output resolution. Default is `1K`. Use `2K`/`4K`
  for posters, print, or detailed infographics with fine text.
- `--image <path>` — provide a reference/input image to **edit or combine**.
  Repeatable: pass `--image` multiple times to merge subjects, keep a character
  consistent, or transfer a style. The prompt then describes the desired change.
- `--fast` — use the faster, cheaper Flash model for quick drafts/iteration.
  Default (omit it) uses Nano Banana Pro for best text and fidelity.
- `--provider <gemini|atlas>` — select the API provider. Gemini is the default.
  Atlas uses `google/nano-banana-pro/text-to-image-developer` and supports
  text-to-image only; do not combine it with `--image` or `--fast`.

**Examples:**

```bash
# A 9:16 phone wallpaper at 2K
python "$CLAUDE_PLUGIN_ROOT/scripts/generate.py" "ENHANCED_PROMPT" --aspect-ratio 9:16 --resolution 2K

# Edit an existing photo
python "$CLAUDE_PLUGIN_ROOT/scripts/generate.py" "Replace the background with a snowy mountain range at golden hour, keep the subject unchanged" --image portrait.png

# Combine two reference images
python "$CLAUDE_PLUGIN_ROOT/scripts/generate.py" "Put the product from the first image onto the marble countertop from the second image, studio lighting" --image product.png --image kitchen.png
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
"A hyper-realistic wide shot of a rainy cyberpunk street in Tokyo at night. Neon signs reflect in the puddles. One prominent holographic sign in the foreground reads 'CYBER NOODLES' in bright pink katakana and English. Steam rises from street vents. Cinematic lighting, high contrast, 8k resolution."

## Setup Requirements

1. Set the GEMINI_API_KEY environment variable:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```
   Get a key at https://aistudio.google.com/apikey

2. Python 3 is required. The script auto-installs its dependencies
   (`google-genai`, and `pillow` when editing reference images) on first run.
   To install them ahead of time:
   ```bash
   pip install -r "$CLAUDE_PLUGIN_ROOT/requirements.txt"
   ```

3. Optional: to use the Atlas Cloud text-to-image provider, set one of:
   ```bash
   export ATLASCLOUD_API_KEY="your-key-here"
   export ATLAS_CLOUD_API_KEY="your-key-here"
   ```

## Error Handling

The script handles common errors:
- Missing provider API key (exits with a clear message)
- API failures (network issues, invalid requests)
- Image download failures
- File write permissions

All errors include helpful messages for troubleshooting.

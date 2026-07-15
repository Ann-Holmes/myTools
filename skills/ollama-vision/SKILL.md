---
name: ollama-vision
description: "Comprehensive image skill: describe, extract, crop, and annotate images by calling Ollama directly. Use when the user needs to understand an image (describe contents, read text, analyze charts/diagrams/screenshots/photos/UI mockups), extract structured data from images (tables, forms, charts to JSON/CSV), extract or crop specific objects/regions from photos, or annotate images with bounding boxes. Always triggers on image-analysis requests — the built-in vision tool has limited token budget and no extraction/annotation capability."
allowed-tools: Bash(uv run *ollama_vision.py *) Bash(uv run *ollama_crop.py *) Bash(uv run *ollama_draw.py *)
---

# Ollama Vision

Analyze, extract, crop, and annotate images by calling Ollama's `/api/generate` endpoint directly.

## Core Principle

**Vision model describes — agent reasons.** Vision models have limited domain knowledge. Do NOT ask them to identify specific entities, interpret results, or draw conclusions. Ask them to describe what they see: text, labels, colors, positions, structures, annotations. You handle all reasoning, identification, and interpretation.

**Language**: Respond in the same language the user is using.

## Capabilities

### 1. Image Description

Describe an entire image in detail. Tailor the prompt to the image type for best results:

**Charts / graphs**: "Describe this chart in detail: chart type, axis labels, scales, data series, legends, grid lines, and any annotations or callouts."

**Screenshots**: "Describe everything visible in this screenshot: windows, dialogs, buttons, text fields, menus, text content, and the layout of UI elements."

**Photos**: "Describe this photo in detail: main subjects, background, colors, lighting, any text visible, and notable objects or people."

**UI design mockups**: "Describe this UI design: layout structure, all components (buttons, inputs, cards, navigation), text labels, colors, spacing patterns, and visual hierarchy."

```bash
uv run scripts/ollama_vision.py image.png "Describe every detail of this <chart/screenshot/photo/UI>. <specific question>"
```

Or pipe the question from stdin:

```bash
echo "Describe this figure in detail" | uv run scripts/ollama_vision.py image.png -
```

### 2. Structured Extraction

Extract data from images into structured formats (JSON, CSV, tables). Useful for tables in screenshots, chart data, form fields, or any structured visual information.

Key: explicitly request a specific output format in the prompt.

**Table extraction**:
```bash
uv run scripts/ollama_vision.py table.png "Extract the data from this table. Return as a JSON array of objects, where each object represents one row with column headers as keys."
```

**Chart data extraction**:
```bash
uv run scripts/ollama_vision.py chart.png "Read all visible data from this chart. Return the values as a CSV string with columns: category, value."
```

**Form / UI field extraction**:
```bash
uv run scripts/ollama_vision.py form.png "List every form field visible in this screenshot. Return as JSON: [{label, type, options if dropdown, current_value if visible}]"
```

Always ask for a specific JSON/CSV schema in the prompt — do not rely on the model to guess the output format.

### 3. Object Extraction (Crop)

Crop a specific region or object from an image. The vision model locates the region by description, then Pillow crops it.

```bash
uv run scripts/ollama_crop.py photo.jpg "the phone on the right side" cropped.png
```

**Crop from the original image before any resizing.** Coordinates map to original pixel dimensions. Compression or resizing changes pixel coordinates.

### 4. Object Annotation (Draw)

Locate objects in an image and draw bounding boxes with labels. The vision model identifies regions and returns coordinates; Pillow draws the annotations.

```bash
uv run scripts/ollama_draw.py photo.jpg "all the people in this photo" annotated.png
uv run scripts/ollama_draw.py --color blue screenshot.png "every button in the toolbar" toolbar_buttons.png
```

Available colors: red, green, blue, yellow, orange, cyan, magenta, white, black (or any hex color).

## Scripts

All scripts use stdlib `urllib` to call Ollama at `http://localhost:11434/api/generate`. Model selection (priority): `-m` flag → `OLLAMA_VISION_MODEL` env var → `qwen3.5:9b`.

| Script | Purpose | Dependencies |
|--------|---------|-------------|
| `scripts/ollama_vision.py` | Full image analysis / description / structured extraction | None (stdlib) |
| `scripts/ollama_crop.py` | Locate region by description and crop | Pillow (PEP 723) |
| `scripts/ollama_draw.py` | Locate objects and draw bounding boxes | Pillow (PEP 723) |

All scripts use PEP 723 inline metadata — `uv run <script>` auto-resolves dependencies.

## Good vs Bad Questions

Good (any output format, any language):
- "Describe every visible element in panel A: ribbon structure, highlighted side chains, labels, and connecting lines."
- "Read all text labels in this figure. List every annotation shown."
- "Extract the data from this table as JSON: [{column1: value, ...}]"
- "Describe the layout and all UI components in this screenshot."

Bad:
- "What protein is this?" — forces hallucination
- "Explain the significance of these results" — interpretation, not observation
- "Is this UI design good?" — subjective judgment, not description

## Notes

- **Endpoint**: Ollama `/api/generate` (NOT `/api/chat`). The `response` field contains the output.
- **`think: false`**: Disables thinking phase for ~15x faster image analysis.
- **`temperature: 0.3`**: Reduces repetitive loops that small models are prone to in long responses.
- **`num_predict: 32000`**: Token budget for detailed figures. Response is truncated when `done` is false.
- **Timeout**: 300s. First request (model warm-up) may take longer.
- **Large images (>2MB)**: Avoid compressing if you also need to crop or annotate — compression changes pixel coordinates.

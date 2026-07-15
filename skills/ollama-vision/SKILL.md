---
name: ollama-vision
description: "Bypass Hermes vision_analyze 2000-token cap — call Ollama directly for full-resolution image analysis. Use when the user needs detailed description of an image (figures, charts, protein structures, diagrams) where the built-in tool would truncate."
---

# Ollama Vision

Analyze images at full resolution by calling Ollama's native `/api/generate` endpoint directly. This bypasses the built-in `vision_analyze` tool which hardcodes `max_tokens: 2000` (and thus truncates detailed responses). The key advantage of `/api/generate` is the `think: false` parameter, which disables the model's thinking phase for ~15x faster image analysis.

## Core Principle

**Vision model is for objective description — reasoning is for the agent.** Vision models have limited domain knowledge. Do NOT ask them to identify proteins, interpret results, or draw conclusions. Instead, ask them to describe exactly what they see — text, labels, colors, positions, structures, arrows, annotations. You (the agent) handle all reasoning and identification.

**Language**: Use whichever language the user is using. The vision model will respond in the same language as the question.

Good questions (any language works):
- "Describe every visible element in panel A: ribbon structure, highlighted side chains, labels, and connecting lines."
- "Read all text labels in this figure. List every annotation shown."
- "Describe the secondary structure in panel B — which regions are β-sheet and which α-helix?"

Bad questions:
- ❌ "What protein is this?" — forces the model to guess and hallucinate
- ❌ "Explain the significance of these mutations" — reasoning task, not description
- ❌ "What biological process does this figure show?" — interpretation, not observation

## Trigger

Use when:
- User sends an image and asks for detailed description/analysis
- User says "use ollama-vision" or "直接用 Ollama 读图"
- The image is complex (multi-panel figures, diagrams, tables, protein structures) and you suspect 2000 tokens won't be enough

## Steps

### 1. Locate the image

Image path from the user's message.

### 2. (Optional) Crop a sub-region first

If you only need a specific region (e.g., a phone mockup, a chart from a screenshot), crop it first using the vision model to identify coordinates:

```bash
uv run --with Pillow python3 /home/hzl/Work/Tmp/cc-workspace/.claude/skills/ollama-vision/scripts/ollama_crop.py \
  "/path/to/image.jpg" \
  "the phone mockup on the right side" \
  /tmp/cropped.png
```

The vision model returns pixel coordinates as JSON, and the script crops with Pillow.

**Important**: Crop from the original image BEFORE any resizing. Coordinates map to the original image dimensions.

### 3. Analyze the image

```bash
uv run python3 /home/hzl/Work/Tmp/cc-workspace/.claude/skills/ollama-vision/scripts/ollama_vision.py \
  "/path/to/image.jpg" \
  "Describe every detail of this image. <user's specific question>"
```

Or pipe the question from stdin:
```bash
echo "Describe this figure" | \
  uv run python3 /home/hzl/Work/Tmp/cc-workspace/.claude/skills/ollama-vision/scripts/ollama_vision.py \
  /path/to/image.jpg -
```

The script handles base64 encoding, API call, and prints the full response to stdout (up to 32000 tokens).

**Fallback (if `uv` is not available):** Use `python3` directly. The vision script uses only stdlib and does not require additional dependencies.

### 4. Present the result

The output is the full, untruncated analysis (up to 32000 tokens).

## Notes

- **Use `uv run python3`** for all Python calls. The vision script uses stdlib only; the crop script needs `--with Pillow`.
- **Do not compress before cropping**: Compression changes pixel coordinates. Crop first from the original image, then compress if needed.
- **Endpoint**: Ollama native `/api/generate` (NOT `/api/chat` or `/v1/chat/completions`). The `response` field contains the full output.
- **`think: false`**: Disabling thinking for image description is the key to speed — ~9s vs ~2min for a 612KB image. Qwen3.5's `think` mode puts image analysis in the thinking phase; with `think: false`, it generates directly into `response`.
- **`temperature: 0.3`**: Reduces repetitive loops that 9B models are prone to in long responses.
- **`num_predict: 32000`**: Token budget for very detailed figures. Response is truncated when `done` is false due to token limit.
- **Vision model → description; Agent → reasoning**: Qwen3.5:9b describes what it sees. You interpret, identify, and reason from the description. Never ask the vision model to identify proteins or draw conclusions.
- **Response time**: Scales with token count. Default timeout is 300s. If the model is warming up (first request), it may take longer.
- **Large images**: Avoid compressing if you need to crop. Only compress >2MB images when full-image analysis is the goal.

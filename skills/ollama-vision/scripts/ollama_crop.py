#!/usr/bin/env python3
"""Ask vision model to locate a region and crop it from the image.

Usage:
    ollama_crop.py <image> <description> [output]
    ollama_crop.py -m gemma4:e4b photo.jpg "the phone on the right" phone.png

Model (priority):
    1. -m / --model flag
    2. OLLAMA_VISION_MODEL env var
    3. Default: qwen3.5:9b

Requires: Pillow (uv run --with Pillow python3 ollama_crop.py ...)
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3.5:9b"
TIMEOUT = 300


def build_prompt(description, img_width, img_height):
    return (
        f"Look at this image. I need to crop exactly ONE specific region from it.\n"
        f"The region to crop: \"{description}\"\n\n"
        f"Image dimensions: {img_width}×{img_height} pixels.\n\n"
        f"Return ONLY a JSON object with bounding box as PERCENTAGES (0-100) of image width/height.\n"
        f"x1=0 means left edge, x2=100 means right edge. y1=0 means top, y2=100 means bottom.\n\n"
        f'Format: {{"x1_pct": <number>, "y1_pct": <number>, "x2_pct": <number>, "y2_pct": <number>}}\n\n'
        f"Example: the left third of the image → {{\"x1_pct\": 0, \"y1_pct\": 0, \"x2_pct\": 33, \"y2_pct\": 100}}\n\n"
        f"Return ONLY the JSON. No markdown, no explanation, no backticks."
    )


def parse_json_response(text):
    """Extract JSON from model response, handling markdown wrapping and both formats."""
    text = text.strip()

    def try_parse(s):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return None

    result = try_parse(text)
    if result:
        return result

    m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if m:
        result = try_parse(m.group(1))
        if result:
            return result

    for key_pattern in [r'"x1_pct"', r'"x1"']:
        m = re.search(r'\{[^{}]*' + key_pattern + r'[^{}]*\}', text, re.DOTALL)
        if m:
            result = try_parse(m.group(0))
            if result:
                return result

    return None


def resolve_coords(coords, img_width, img_height):
    """Convert coordinates to absolute pixels. Handles both percentage and pixel formats.

    If keys end with _pct but values are > 100, the model likely returned pixel values
    mislabeled as percentages — treat them as pixels.
    """
    if "x1_pct" in coords:
        vals = [coords["x1_pct"], coords["y1_pct"], coords["x2_pct"], coords["y2_pct"]]
        # Heuristic: if any pct value > 100, model returned pixels mislabeled as pct
        if any(v > 100 for v in vals):
            return int(vals[0]), int(vals[1]), int(vals[2]), int(vals[3])
        return (
            int(round(coords["x1_pct"] / 100.0 * img_width)),
            int(round(coords["y1_pct"] / 100.0 * img_height)),
            int(round(coords["x2_pct"] / 100.0 * img_width)),
            int(round(coords["y2_pct"] / 100.0 * img_height)),
        )
    # Pixel format
    return int(coords["x1"]), int(coords["y1"]), int(coords["x2"]), int(coords["y2"])


def main():
    parser = argparse.ArgumentParser(description="Crop image region identified by Ollama vision model")
    parser.add_argument(
        "-m", "--model",
        default=os.environ.get("OLLAMA_VISION_MODEL", DEFAULT_MODEL),
        help=f"Model name (default: {DEFAULT_MODEL}, env: OLLAMA_VISION_MODEL)",
    )
    parser.add_argument("image", help="Path to input image")
    parser.add_argument("description", help="Natural language description of the region to crop")
    parser.add_argument("output", nargs="?", default="crop.png", help="Output path (default: crop.png)")
    args = parser.parse_args()

    try:
        from PIL import Image
    except ImportError:
        print("Error: Pillow is required. Run with: uv run --with Pillow python3 ollama_crop.py ...", file=sys.stderr)
        sys.exit(1)

    with Image.open(args.image) as img:
        img_width, img_height = img.size

    with open(args.image, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    prompt = build_prompt(args.description, img_width, img_height)

    payload = {
        "model": args.model,
        "prompt": prompt,
        "images": [img_b64],
        "think": False,
        "options": {"num_predict": 256, "temperature": 0.1},
        "stream": False,
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    print(f"Asking {args.model} to locate: \"{args.description}\"...", file=sys.stderr)
    try:
        resp_data = urllib.request.urlopen(req, timeout=TIMEOUT).read()
    except urllib.error.URLError as e:
        print(f"Error: cannot connect to Ollama at {OLLAMA_URL} ({e.reason})", file=sys.stderr)
        sys.exit(1)
    except TimeoutError:
        print(f"Error: request timed out after {TIMEOUT}s", file=sys.stderr)
        sys.exit(1)

    resp = json.loads(resp_data)
    text = resp.get("response", "")
    if not text:
        print("Error: empty response from Ollama", file=sys.stderr)
        sys.exit(1)

    coords = parse_json_response(text)
    if coords is None:
        print("Error: could not parse coordinates from model response:", file=sys.stderr)
        print(text[:500], file=sys.stderr)
        sys.exit(1)

    x1, y1, x2, y2 = resolve_coords(coords, img_width, img_height)
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(img_width, x2)
    y2 = min(img_height, y2)

    if x1 >= x2 or y1 >= y2:
        print(f"Error: invalid crop region ({x1},{y1})-({x2},{y2})", file=sys.stderr)
        sys.exit(1)

    print(f"Crop: ({x1},{y1})-({x2},{y2}) [{x2 - x1}×{y2 - y1}]", file=sys.stderr)

    with Image.open(args.image) as img:
        img.crop((x1, y1, x2, y2)).save(args.output)

    print(f"Saved: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()

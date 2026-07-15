#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""Annotate image regions identified by Ollama vision model.

Usage:
    uv run ollama_draw.py <image> <description> [output]
    uv run ollama_draw.py -m gemma4:e4b photo.jpg "the cat and the dog" annotated.png
    uv run ollama_draw.py --color red photo.jpg "all buttons" buttons.png

Model (priority):
    1. -m / --model flag
    2. OLLAMA_VISION_MODEL env var
    3. Default: qwen3.5:9b
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
COLORS = {
    "red": "#FF0000", "green": "#00FF00", "blue": "#0066FF",
    "yellow": "#FFD700", "orange": "#FF8C00", "cyan": "#00FFFF",
    "magenta": "#FF00FF", "white": "#FFFFFF", "black": "#000000",
}


def build_prompt(description):
    return (
        f"Locate \"{description}\" in this image. "
        f"Return bbox_2d coordinates and label in JSON format."
    )


def parse_json_response(text):
    text = text.strip()

    def try_parse(s):
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return None

    result = try_parse(text)
    if result:
        return result

    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        return try_parse(m.group(1))

    m = re.search(r"\[.*?\]", text, re.DOTALL)
    if m:
        return try_parse(m.group(0))

    return None


def resolve_coords(obj, img_width, img_height):
    """Convert bbox_2d from 0-999 normalized space to pixel coordinates."""
    bbox = obj["bbox_2d"]
    return (
        int(round(bbox[0] / 999.0 * img_width)),
        int(round(bbox[1] / 999.0 * img_height)),
        int(round(bbox[2] / 999.0 * img_width)),
        int(round(bbox[3] / 999.0 * img_height)),
    )


def main():
    parser = argparse.ArgumentParser(description="Annotate image with Ollama vision model")
    parser.add_argument(
        "-m", "--model",
        default=os.environ.get("OLLAMA_VISION_MODEL", DEFAULT_MODEL),
        help=f"Model name (default: {DEFAULT_MODEL}, env: OLLAMA_VISION_MODEL)",
    )
    parser.add_argument(
        "--color", default="red",
        help=f"Bounding box color. Choices: {', '.join(COLORS)} (default: red)",
    )
    parser.add_argument("image", help="Path to input image")
    parser.add_argument("description", help="Natural language description of what to annotate")
    parser.add_argument("output", nargs="?", default="annotated.png", help="Output path (default: annotated.png)")
    args = parser.parse_args()

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Error: Pillow is required.", file=sys.stderr)
        sys.exit(1)

    color = COLORS.get(args.color.lower(), args.color)

    with Image.open(args.image) as img:
        img_width, img_height = img.size

    with open(args.image, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    prompt = build_prompt(args.description)

    payload = {
        "model": args.model,
        "prompt": prompt,
        "images": [img_b64],
        "think": False,
        "options": {"num_predict": 1024, "temperature": 0.1},
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

    objects = parse_json_response(text)
    if not objects:
        print("Error: could not parse coordinates from model response:", file=sys.stderr)
        print(text[:500], file=sys.stderr)
        sys.exit(1)

    if isinstance(objects, dict):
        objects = [objects]

    drawn = 0
    with Image.open(args.image) as img:
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except (OSError, IOError):
            font = ImageFont.load_default()

        for obj in objects:
            if "bbox_2d" not in obj:
                print(f"  Skipping object without bbox_2d: {obj}", file=sys.stderr)
                continue

            x1, y1, x2, y2 = resolve_coords(obj, img_width, img_height)
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img_width, x2), min(img_height, y2)
            if x1 >= x2 or y1 >= y2:
                print(f"  Skipping invalid region ({x1},{y1})-({x2},{y2})", file=sys.stderr)
                continue

            label = obj.get("label", "")
            draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
            if label:
                tb = draw.textbbox((x1, y1 - 16), label, font=font)
                draw.rectangle(tb, fill=color)
                draw.text((x1, y1 - 16), label, fill="white", font=font)
            print(f"  {label}: ({x1},{y1})-({x2},{y2}) [{x2-x1}x{y2-y1}]", file=sys.stderr)
            drawn += 1

        img.save(args.output)

    print(f"Annotated {drawn} region(s) -> {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()

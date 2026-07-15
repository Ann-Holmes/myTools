#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
"""Analyze images with a local Ollama vision model via /api/generate.

Usage:
    uv run ollama_vision.py <image> [question]
    uv run ollama_vision.py -m gemma4:e4b <image> "Describe this figure"
    uv run ollama_vision.py <image> -          # read question from stdin

Model (priority):
    1. -m / --model flag
    2. OLLAMA_VISION_MODEL env var
    3. Default: qwen3.5:9b
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3.5:9b"
NUM_PREDICT = 32000
TEMPERATURE = 0.3
TIMEOUT = 300


def main():
    parser = argparse.ArgumentParser(description="Analyze images with Ollama vision model")
    parser.add_argument(
        "-m", "--model",
        default=os.environ.get("OLLAMA_VISION_MODEL", DEFAULT_MODEL),
        help=f"Model name (default: {DEFAULT_MODEL}, env: OLLAMA_VISION_MODEL)",
    )
    parser.add_argument("image", help="Path to image file")
    parser.add_argument(
        "question", nargs="?", default="Fully describe every detail of this image.",
        help="Question to ask about the image. Use '-' to read from stdin.",
    )
    args = parser.parse_args()

    question = args.question
    if question == "-":
        question = sys.stdin.read().strip()

    with open(args.image, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    payload = {
        "model": args.model,
        "prompt": question,
        "images": [img_b64],
        "think": False,
        "options": {"num_predict": NUM_PREDICT, "temperature": TEMPERATURE},
        "stream": False,
    }

    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )

    print(f"Analyzing image with {args.model}...", file=sys.stderr)
    try:
        resp_data = urllib.request.urlopen(req, timeout=TIMEOUT).read()
    except urllib.error.URLError as e:
        print(f"Error: cannot connect to Ollama at {OLLAMA_URL} — is it running? ({e.reason})", file=sys.stderr)
        sys.exit(1)
    except TimeoutError:
        print(f"Error: request timed out after {TIMEOUT}s", file=sys.stderr)
        sys.exit(1)

    resp = json.loads(resp_data)
    response = resp.get("response", "")
    if not response:
        if "error" in resp:
            print(f"Error from Ollama: {resp['error']}", file=sys.stderr)
        else:
            print("Error: empty response from Ollama", file=sys.stderr)
        sys.exit(1)

    print(response)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate or edit images with OpenRouter's GPT Image 2.5 Sunburst model.

Calls the OpenRouter Images API (https://openrouter.ai/api/v1/images) because
openai/gpt-image-2.5-sunburst cannot be used with the chat/completions endpoint.

Usage:
    gptimage.py "PROMPT" [--aspect-ratio 16:9] [--quality high] [-n 2] [--dir out]
    gptimage.py "PROMPT" --reference input.png [-o edited.png]

The API key is read from OPENROUTER_API_KEY, OpenCode's credential store via
`opencode auth export` (V2), or the legacy ~/.local/share/opencode/auth.json.
"""

import argparse
import base64
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

API_URL = "https://openrouter.ai/api/v1/images"
MODEL = "openai/gpt-image-2.5-sunburst"

EXTENSIONS = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
}


def key_from_opencode():
    """Read the active OpenRouter key from OpenCode's credential store.

    OpenCode V2 keeps provider credentials in its database instead of
    ~/.local/share/opencode/auth.json, so ask the CLI for them.
    """
    executable = shutil.which("opencode")
    if not executable:
        return None
    try:
        completed = subprocess.run(
            [executable, "auth", "export"],
            capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    try:
        exported = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    entries = exported if isinstance(exported, list) else [exported]
    fallback = None
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        integration = entry.get("integrationID") or entry.get("integration_id")
        if integration != "openrouter":
            continue
        value = entry.get("value")
        key = None
        if isinstance(value, dict):
            for field in ("key", "apiKey", "access"):
                candidate = value.get(field)
                if isinstance(candidate, str) and candidate:
                    key = candidate
                    break
        elif isinstance(value, str) and value:
            key = value
        if key:
            if entry.get("active", True):
                return key
            if fallback is None:
                fallback = key
    return fallback


def find_api_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    key = key_from_opencode()
    if key:
        return key
    auth_path = os.path.expanduser("~/.local/share/opencode/auth.json")
    try:
        with open(auth_path, encoding="utf-8") as handle:
            credentials = json.load(handle)
    except (OSError, json.JSONDecodeError):
        credentials = {}
    entry = credentials.get("openrouter")
    if isinstance(entry, dict):
        for field in ("key", "apiKey", "access"):
            value = entry.get(field)
            if isinstance(value, str) and value:
                return value
    sys.exit("error: no OpenRouter API key: set OPENROUTER_API_KEY or connect "
             "OpenRouter in OpenCode")


def file_to_data_url(path):
    mime, _ = mimetypes.guess_type(path)
    if mime is None or not mime.startswith("image/"):
        mime = "image/png"
    with open(path, "rb") as handle:
        return f"data:{mime};base64,{base64.b64encode(handle.read()).decode()}"


def build_payload(args):
    payload = {"model": MODEL, "prompt": args.prompt}
    if args.aspect_ratio != "auto":
        payload["aspect_ratio"] = args.aspect_ratio
    if args.quality != "auto":
        payload["quality"] = args.quality
    if args.background != "auto":
        payload["background"] = args.background
    if args.n != 1:
        payload["n"] = args.n
    if args.compression is not None:
        payload["output_compression"] = args.compression
    if args.reference:
        payload["input_references"] = [
            {"type": "image_url", "image_url": {"url": file_to_data_url(path)}}
            for path in args.reference
        ]
    return payload


def post_json(payload, key, timeout):
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://opencode.ai/",
            "X-Title": "opencode gptimage",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        try:
            detail = json.load(error).get("error", {})
            message = detail.get("message", error.reason)
        except (ValueError, AttributeError):
            message = error.reason
        sys.exit(f"error: OpenRouter returned HTTP {error.code}: {message}")
    except urllib.error.URLError as error:
        sys.exit(f"error: could not reach OpenRouter: {error.reason}")


def next_path(directory, stem, index, extension):
    suffix = "" if index == 0 else f"-{index + 1}"
    candidate = os.path.join(directory, f"{stem}{suffix}.{extension}")
    counter = 1
    while os.path.exists(candidate):
        counter += 1
        candidate = os.path.join(
            directory, f"{stem}{suffix}-{counter}.{extension}")
    return candidate


def save_images(data, out_file, directory, stem):
    if out_file and len(data) != 1:
        sys.exit("error: --out needs exactly one image; got "
                 f"{len(data)} (remove --out or set -n 1)")
    saved = []
    for index, image in enumerate(data):
        extension = EXTENSIONS.get(image.get("media_type") or "", "png")
        if out_file:
            path = out_file
        else:
            path = next_path(directory, stem, index, extension)
        if image.get("b64_json"):
            blob = base64.b64decode(image["b64_json"])
        elif image.get("url"):
            with urllib.request.urlopen(image["url"], timeout=300) as response:
                blob = response.read()
        else:
            sys.exit("error: OpenRouter returned an image without data")
        with open(path, "wb") as handle:
            handle.write(blob)
        saved.append(os.path.abspath(path))
    return saved


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate or edit images with OpenRouter's GPT Image 2.5 "
                    "Sunburst model (openai/gpt-image-2.5-sunburst).")
    parser.add_argument("prompt", nargs="?",
                        help="image description; use '-' to read it from stdin")
    parser.add_argument("--aspect-ratio", default="auto",
                        choices=["auto", "1:1", "3:2", "2:3", "4:3", "3:4",
                                 "16:9", "9:16", "21:9"],
                        help="output aspect ratio (default: auto)")
    parser.add_argument("--quality", default="auto",
                        choices=["auto", "low", "medium", "high", "xhigh",
                                 "max"],
                        help="rendering quality (default: auto)")
    parser.add_argument("--background", default="auto",
                        choices=["auto", "transparent", "opaque"],
                        help="background treatment; transparent needs "
                             "png/webp output (default: auto)")
    parser.add_argument("-n", type=int, default=1, choices=range(1, 11),
                        metavar="1-10",
                        help="number of images to generate (default: 1)")
    parser.add_argument("--compression", type=int, metavar="0-100",
                        help="compression for webp/jpeg output")
    parser.add_argument("--reference", action="append", default=[],
                        metavar="FILE",
                        help="reference image for editing; repeat up to 16 "
                             "times")
    parser.add_argument("-o", "--out", metavar="FILE",
                        help="exact output file (only with a single image)")
    parser.add_argument("-d", "--dir", default=".", metavar="DIR",
                        help="directory for generated files (default: .)")
    parser.add_argument("--timeout", type=int, default=300,
                        help="request timeout in seconds (default: 300)")
    args = parser.parse_args()
    if args.prompt is None:
        parser.error("a prompt is required")
    if args.prompt == "-":
        args.prompt = sys.stdin.read().strip()
        if not args.prompt:
            parser.error("stdin did not contain a prompt")
    if len(args.reference) > 16:
        parser.error("at most 16 --reference images are supported")
    for path in args.reference:
        if not os.path.isfile(path):
            parser.error(f"reference image not found: {path}")
    return args


def main():
    args = parse_args()
    key = find_api_key()
    payload = build_payload(args)
    result = post_json(payload, key, args.timeout)

    data = result.get("data") or []
    if not data:
        sys.exit("error: OpenRouter returned no images")
    os.makedirs(args.dir, exist_ok=True)
    stem = f"gptimage-{time.strftime('%Y%m%d-%H%M%S')}"
    saved = save_images(data, args.out, args.dir, stem)

    for path in saved:
        print(path)
    usage = result.get("usage") or {}
    cost = usage.get("cost")
    if isinstance(cost, (int, float)):
        print(f"cost: ${cost:.4f}", file=sys.stderr)


if __name__ == "__main__":
    main()

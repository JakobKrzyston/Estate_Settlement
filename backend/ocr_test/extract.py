"""OCR test extraction: send synthetic certificate images to Anthropic vision API with 24-field prompt."""

import base64
import json
import os
import time
from pathlib import Path

import anthropic
from dotenv import find_dotenv, load_dotenv

from .prompts import EXTRACT_PROMPT

load_dotenv(find_dotenv())

_MODEL = os.environ.get("EXTRACTION_MODEL", "claude-sonnet-4-6")


def _detect_media_type(path: Path) -> str:
    """Return MIME type for an image file."""
    types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mt = types.get(path.suffix.lower())
    if mt is None:
        raise ValueError(f"Unsupported image type: {path.suffix!r}")
    return mt


def _parse_json_response(text: str) -> dict:
    """Extract a JSON object from the model response, stripping any surrounding text."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse model response as JSON: {text[:200]!r}")


def extract_certificate(image_path: str) -> dict:
    """Extract all 24 death certificate fields from a synthetic certificate image.

    Args:
        image_path: Path to a PNG image file.

    Returns:
        Flat dict with keys matching the 24 fields in the test prompt.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {image_path}")

    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    media_type = _detect_media_type(path)

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
                {"type": "text", "text": EXTRACT_PROMPT},
            ],
        }],
    )

    return _parse_json_response(response.content[0].text)


def extract_with_metrics(image_path: str) -> dict:
    """Like extract_certificate but also returns API usage metadata.

    Args:
        image_path: Path to a PNG image file.

    Returns:
        Dict with keys: result (extracted fields), model, input_tokens,
        output_tokens, latency_ms.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {image_path}")

    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    media_type = _detect_media_type(path)

    client = anthropic.Anthropic()
    t0 = time.perf_counter()
    response = client.messages.create(
        model=_MODEL,
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data}},
                {"type": "text", "text": EXTRACT_PROMPT},
            ],
        }],
    )
    latency_ms = round((time.perf_counter() - t0) * 1000)

    return {
        "result": _parse_json_response(response.content[0].text),
        "model": _MODEL,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency_ms": latency_ms,
    }

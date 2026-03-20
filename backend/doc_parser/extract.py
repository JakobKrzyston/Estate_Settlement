"""Extraction pipeline: parse death certificate PDFs/images into structured JSON via Anthropic vision API."""

import base64
import json
import time
from pathlib import Path
from typing import Literal, Optional

import anthropic
import fitz  # pymupdf
from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel, Field, field_validator

from .prompts import EXTRACT_PROMPT

load_dotenv(find_dotenv())


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class DeceasedData(BaseModel):
    """Fields describing the deceased individual on the certificate."""

    full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    date_of_death: Optional[str] = None
    ssn_last4: Optional[str] = Field(default=None, max_length=4)
    cause_of_death: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    surviving_spouse: Optional[str] = None


class FilerData(BaseModel):
    """The informant or applicant who filed the document."""

    name: Optional[str] = None
    relationship: Optional[Literal["surviving_spouse", "adult_child", "executor", "other"]] = None
    address: Optional[str] = None

    @field_validator("relationship", mode="before")
    @classmethod
    def _normalize(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        _MAP = {
            "spouse": "surviving_spouse", "wife": "surviving_spouse",
            "husband": "surviving_spouse", "son": "adult_child",
            "daughter": "adult_child", "child": "adult_child",
            "personal representative": "executor", "executor": "executor",
        }
        return _MAP.get(str(v).lower().strip(), "other")


class CertificateData(BaseModel):
    """Top-level extraction result from a death certificate document."""

    deceased: DeceasedData = Field(default_factory=DeceasedData)
    filer: FilerData = Field(default_factory=FilerData)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_image_media_type(path: Path) -> str:
    suffix = path.suffix.lower()
    types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    if suffix not in types:
        raise ValueError(f"Unsupported file type: {path.suffix!r}")
    return types[suffix]


def _build_content_block(path: Path, page: int) -> dict:
    if path.suffix.lower() == ".pdf":
        doc = fitz.open(str(path))
        if page >= len(doc):
            raise IndexError(f"Page {page} out of range — document has {len(doc)} page(s)")
        png_bytes = doc[page].get_pixmap(dpi=200).tobytes("png")
        data = base64.standard_b64encode(png_bytes).decode("utf-8")
        media_type = "image/png"
    else:
        data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
        media_type = _detect_image_media_type(path)

    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data},
    }


def _parse_json_response(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Strip markdown fences or surrounding prose
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Could not parse model response as JSON: {text[:200]!r}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_certificate(image_path: str, page: int = 0) -> dict:
    """Extract structured fields from a death certificate PDF or image.

    Args:
        image_path: Path to a PDF or image file.
        page: For multi-page PDFs, the 0-indexed page containing the certificate.

    Returns:
        dict with keys matching CertificateData fields plus 'confidence'.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {image_path}")

    client = anthropic.Anthropic()
    content_block = _build_content_block(path, page)

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": EXTRACT_PROMPT},
                ],
            }],
        )
    except anthropic.APIError as exc:
        raise RuntimeError(f"Anthropic API error: {exc}") from exc

    raw_text = response.content[0].text
    parsed = _parse_json_response(raw_text)
    result = CertificateData.model_validate(parsed)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Metrics-aware extraction (used by eval harness)
# ---------------------------------------------------------------------------

_MODEL = "claude-sonnet-4-6"


def _parse_certificate_with_metrics(image_path: str, page: int = 0) -> dict:
    """Like parse_certificate but also returns API usage metadata.

    Returns a dict with keys:
        result         – extracted fields (same as parse_certificate return value)
        model          – model ID used
        input_tokens   – prompt token count from response.usage
        output_tokens  – completion token count from response.usage
        latency_ms     – wall-clock ms from request send to response received
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {image_path}")

    client = anthropic.Anthropic()
    content_block = _build_content_block(path, page)

    t0 = time.perf_counter()
    try:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": EXTRACT_PROMPT},
                ],
            }],
        )
    except anthropic.APIError as exc:
        raise RuntimeError(f"Anthropic API error: {exc}") from exc
    latency_ms = round((time.perf_counter() - t0) * 1000)

    raw_text = response.content[0].text
    parsed = _parse_json_response(raw_text)
    result = CertificateData.model_validate(parsed)

    return {
        "result": result.model_dump(),
        "model": _MODEL,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "latency_ms": latency_ms,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    SAMPLES_DIR = Path(__file__).parent.parent / "samples"

    ap = argparse.ArgumentParser(description="Extract fields from a death certificate.")
    ap.add_argument(
        "paths",
        nargs="*",
        help="Path(s) to PDF or image files. Defaults to all *.pdf in samples/",
    )
    ap.add_argument("--page", type=int, default=0, help="0-indexed page number (PDF only, default 0)")
    ap.add_argument(
        "--output",
        default="output/results.jsonl",
        help="Output JSON Lines file (default: output/results.jsonl)",
    )
    args = ap.parse_args()

    if args.paths:
        files = [Path(p) for p in args.paths]
    else:
        files = sorted(SAMPLES_DIR.glob("*.pdf"))
        if not files:
            sys.exit(f"No .pdf files found in {SAMPLES_DIR}")

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with out_path.open("w") as fh:
        for file in files:
            record = {"file": str(file), **parse_certificate(str(file), page=args.page)}
            fh.write(json.dumps(record) + "\n")
            print(f"✓ {file.name}", file=sys.stderr)

    print(f"Results written to {out_path}")

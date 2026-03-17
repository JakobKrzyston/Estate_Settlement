import base64
import json
from pathlib import Path
from typing import Optional

import anthropic
import fitz  # pymupdf
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from .prompts import EXTRACT_PROMPT

load_dotenv()


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------

class CertificateData(BaseModel):
    deceased_full_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    date_of_death: Optional[str] = None
    ssn_last4: Optional[str] = Field(default=None, max_length=4)
    cause_of_death: Optional[str] = None
    county: Optional[str] = None
    state: Optional[str] = None
    surviving_spouse: Optional[str] = None
    filer_relationship: Optional[str] = None
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
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Extract fields from a death certificate.")
    ap.add_argument("path", help="Path to a PDF or image file")
    ap.add_argument("--page", type=int, default=0, help="0-indexed page number (PDF only, default 0)")
    args = ap.parse_args()

    print(json.dumps(parse_certificate(args.path, page=args.page), indent=2))

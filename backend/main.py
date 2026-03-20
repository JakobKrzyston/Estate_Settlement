"""FastAPI app: /parse and /generate endpoints for death certificate extraction."""

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from doc_parser.extract import parse_certificate

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}


@app.post("/parse")
async def parse(file: UploadFile = File(...)) -> dict:
    """Accept a PDF or image upload and return extracted certificate fields.

    Args:
        file: Uploaded PDF, JPG, or PNG file.

    Returns:
        Dict with deceased, filer, and confidence fields.

    Raises:
        HTTPException: 400 for unsupported file type, 500 for extraction errors.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    suffix = Path(file.filename or "upload").suffix or ".tmp"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        return parse_certificate(tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        os.unlink(tmp_path)


class GenerateRequest(BaseModel):
    fields: dict
    institutions: list[str]


@app.post("/generate")
async def generate(req: GenerateRequest) -> dict:
    """Accept confirmed certificate fields and institution list, return letter text.

    Args:
        req: JSON body with 'fields' (flat dict) and 'institutions' (list of keys).

    Returns:
        Dict with 'letters' mapping institution key → letter text.
    """
    letters = {}
    for inst in req.institutions:
        letters[inst] = (
            f"[PLACEHOLDER] Letter for {inst} — [TODO: Implement template].\n\n"
            f"Deceased: {req.fields.get('full_name')}\n"
            f"Date of Death: {req.fields.get('date_of_death')}\n"
            f"SSN Last 4: {req.fields.get('ssn_last4')}\n"
            f"Filer: {req.fields.get('filer_name')} ({req.fields.get('filer_relationship')})"
        )
    return {"letters": letters}

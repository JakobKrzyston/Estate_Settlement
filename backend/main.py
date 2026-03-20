"""FastAPI app: /parse and /generate endpoints for death certificate extraction."""

import io
import os
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from jinja2 import TemplateNotFound
from pydantic import BaseModel

from doc_parser.extract import parse_certificate
from doc_parser.generate import render_letter, render_to_pdf_bytes

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


class ExportPdfRequest(BaseModel):
    institution: str
    fields: dict


def _fields_to_vars(fields: dict) -> dict:
    """Map the flat frontend fields dict to Jinja2 template variable names.

    Args:
        fields: Flat dict sent by the frontend (full_name, filer_name, etc.).

    Returns:
        Dict of template variable names expected by base.html and institution templates.
    """
    last4 = fields.get("ssn_last4", "")
    full_name = fields.get("full_name", "")
    return {
        "deceased_full_name": full_name,
        "account_holder_name": full_name,
        "date_of_birth": fields.get("date_of_birth", ""),
        "date_of_death": fields.get("date_of_death", ""),
        "ssn_last4": last4,
        "deceased_ssn": f"XXX-XX-{last4}" if last4 else "",
        "county": fields.get("county", ""),
        "state": fields.get("state", ""),
        "surviving_spouse": fields.get("surviving_spouse", ""),
        "sender_name": fields.get("filer_name", ""),
        "sender_relationship": fields.get("filer_relationship", ""),
        "sender_address": fields.get("filer_address", ""),
        "sender_phone": "",
        "date": datetime.now().strftime("%B %-d, %Y"),
    }


@app.post("/generate")
async def generate(req: GenerateRequest) -> dict:
    """Accept confirmed certificate fields and institution list, return rendered HTML letters.

    Args:
        req: JSON body with 'fields' (flat dict) and 'institutions' (list of keys).

    Returns:
        Dict with 'letters' mapping institution key → rendered HTML string.
    """
    vars = _fields_to_vars(req.fields)
    letters = {}
    for inst in req.institutions:
        try:
            letters[inst] = render_letter(inst, vars)
        except TemplateNotFound:
            name = inst.replace("_", " ").title()
            letters[inst] = (
                f"<!DOCTYPE html><html><head><style>"
                f"body{{font-family:Georgia,serif;font-size:12pt;line-height:1.6;"
                f"color:#111;max-width:680px;margin:60px auto;padding:0 40px;}}"
                f"</style></head><body>"
                f"<p><em>Letter template for <strong>{name}</strong> is coming soon.</em></p>"
                f"</body></html>"
            )
    return {"letters": letters}


@app.post("/export-pdf")
async def export_pdf_endpoint(req: ExportPdfRequest) -> StreamingResponse:
    """Render an institution letter as a PDF and return it as a file download.

    Args:
        req: JSON body with 'institution' key and 'fields' flat dict.

    Returns:
        PDF file as a streaming response attachment.

    Raises:
        HTTPException: 404 if no template exists for the institution.
    """
    vars = _fields_to_vars(req.fields)
    try:
        html = render_letter(req.institution, vars)
    except TemplateNotFound:
        raise HTTPException(status_code=404, detail=f"No template for {req.institution!r}")
    pdf_bytes = render_to_pdf_bytes(html)
    filename = f"{req.institution}_letter.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

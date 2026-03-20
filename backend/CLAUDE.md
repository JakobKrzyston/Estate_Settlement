# Estate Settlement — Claude Context

## Project Purpose
Full-stack app that extracts structured fields from death certificate PDFs using the Anthropic vision API, then generates notification letters for 15 institution types. Outputs validated JSON via Pydantic models.

## Stack
- **Backend**: Python 3.11+, FastAPI, Anthropic SDK, Pydantic v2, pymupdf (fitz), Jinja2, xhtml2pdf, html2docx
- **Frontend**: React 19, Vite, Tailwind CSS v4 (lives in `../frontend/`)
- **Testing**: pytest (`tests/test_eval.py` — fuzzy field-level scoring against ground truth)
- **Config**: `.env` for API keys (loaded via python-dotenv); env vars for CORS, model selection

## Project Structure
- `main.py` — FastAPI app with endpoints: /parse, /generate, /export-pdf, /export-docx
- `doc_parser/extract.py` — core extraction logic + CLI entry point
- `doc_parser/generate.py` — letter generator: fills Jinja2 templates from extracted data
- `doc_parser/eval.py` — evaluation harness comparing output to ground truth
- `doc_parser/metrics.py` — cost projection and trial result logging
- `doc_parser/prompts.py` — prompt constants
- `templates/` — Jinja2 letter templates: base.html + 15 institution templates (5 .txt, 10 .html)
- `tests/test_eval.py` — pytest eval harness with Levenshtein fuzzy scoring
- `samples/` — test PDFs and `ground_truth.json` (gitignored)
- `output/` — generated result files (gitignored)

## Common Commands
```bash
# Start the API server (dev)
uvicorn main:app --reload

# Run extraction on all sample PDFs
python -m doc_parser.extract

# Run evaluation against ground truth
python -m doc_parser.eval

# Run pytest eval harness
pytest tests/test_eval.py -v
```

## Conventions
- Public extraction functions return plain `dict` (via `model.model_dump()`).
- Use `_parse_certificate_with_metrics()` in eval contexts; `parse_certificate()` elsewhere.
- Model string is pinned as `_MODEL` constant in `extract.py` (configurable via `EXTRACTION_MODEL` env var) — update there only.
- Keep prompts in `prompts.py`, not inline in functions.
- CORS origins are configurable via `CORS_ORIGINS` env var in `main.py`.

## Documentation Standards
- Docstring format: Google-style with `Args:`, `Returns:`, and `Raises:` sections.
- Every public function gets a docstring. Private (`_`) helpers only if the logic isn't obvious from the name.
- Every module gets a one-line module docstring at the top.
- README must stay current: if you change setup steps, CLI flags, or project structure, update it.
- Type hints are required on all function signatures you write or modify.

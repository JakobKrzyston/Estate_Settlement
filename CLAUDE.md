# Estate Settlement — Claude Context

## Project Purpose
Extracts structured fields from death certificate PDFs using the Anthropic vision API. Outputs validated JSON via Pydantic models.

## Stack
- Python 3.x, Anthropic SDK, Pydantic v2, pymupdf (fitz)
- `.env` for API keys (loaded via python-dotenv)
- No test framework yet; evaluation done via `doc_parser/eval.py`

## Project Structure
- `doc_parser/extract.py` — core extraction logic + CLI entry point
- `doc_parser/eval.py` — evaluation harness comparing output to ground truth
- `doc_parser/metrics.py` — field-level scoring helpers
- `doc_parser/prompts.py` — prompt constants
- `samples/` — test PDFs and `ground_truth.json`
- `output/` — generated result files (gitignored)

## Common Commands
```bash
# Run extraction on all sample PDFs
python -m doc_parser.extract

# Run evaluation against ground truth
python -m doc_parser.eval
```

## Conventions
- Public extraction functions return plain `dict` (via `model.model_dump()`).
- Use `_parse_certificate_with_metrics()` in eval contexts; `parse_certificate()` elsewhere.
- Model string is pinned as `_MODEL` constant in `extract.py` — update there only.
- Keep prompts in `prompts.py`, not inline in functions.

## Documentation Standards
- Docstring format: Google-style with `Args:`, `Returns:`, and `Raises:` sections.
- Every public function gets a docstring. Private (`_`) helpers only if the logic isn't obvious from the name.
- Every module gets a one-line module docstring at the top.
- README must stay current: if you change setup steps, CLI flags, or project structure, update it.
- Type hints are required on all function signatures you write or modify.

# Estate Settlement

Extracts structured fields from death certificate PDFs using the Anthropic vision API. Given a PDF or image, the tool returns a validated JSON record containing key fields (name, dates, SSN last 4, county, surviving spouse, etc.) useful for estate administration workflows.

## Setup

**1. Install dependencies**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure API key**

Create a `.env` file in the project root:
```
ANTHROPIC_API_KEY=sk-ant-...
```

## Usage

**Extract from all sample PDFs (writes to `output/results.jsonl`):**
```bash
python -m doc_parser.extract
```

**Extract from specific files:**
```bash
python -m doc_parser.extract samples/TX_Reyes.pdf samples/TX_Thornton.pdf
```

**Options:**
```
--page N       0-indexed page number for multi-page PDFs (default: 0)
--output PATH  Output JSONL file path (default: output/results.jsonl)
```

**Run evaluation against ground truth:**
```bash
python -m doc_parser.eval
```

**Generate filled notification letters from extraction output:**
```bash
# Fill a single template (ssa, medicare, utility, telecom, bank)
python -m doc_parser.generate \
    --results output/results.jsonl \
    --record 0 \
    --template ssa \
    --vars vars.json

# Fill all five templates at once
python -m doc_parser.generate \
    --results output/results.jsonl \
    --record 0 \
    --all \
    --vars vars.json
```

`vars.json` provides supplemental fields not found on the death certificate (sender info, account numbers, etc.):
```json
{
  "sender_name": "Jane Doe",
  "sender_address": "456 Elm St, Austin TX 78701",
  "sender_phone": "(512) 555-1234",
  "date": "March 17, 2026",
  "forwarding_address": "456 Elm St, Austin TX 78701",
  "account_number": "XXXXXX1234",
  "medicare_beneficiary_id": "1EG4-TE5-MK72"
}
```

Certificate fields (`deceased_full_name`, `date_of_death`, `filer_relationship`, etc.) are filled automatically from the extraction output. Any template slot that remains unresolved is left visible as `{{ slot_name }}` so you can see what still needs filling.

Output files are written to `output/letters/<cert_stem>_<template>.txt`.

## Project Structure

```
doc_parser/
  extract.py    Core extraction logic, Pydantic output schema, CLI entry point
  generate.py   Letter generator — fills notification templates from extracted data
  eval.py       Evaluation harness — scores output against ground_truth.json
  metrics.py    Cost projection and trial result logging
  prompts.py    Prompt constants passed to the model
templates/
  death-notification-templates/
    ssa.txt, medicare.txt, utility.txt, telecom.txt, bank.txt
samples/
  *.pdf                 Sample death certificates for testing
  ground_truth.json     Expected field values for evaluation
output/
  results.jsonl         Extraction output (generated, not committed)
  letters/              Filled letter output (generated, not committed)
```

## Output Format

Each line of `results.jsonl` is a JSON object with the following fields:

| Field | Type | Description |
|---|---|---|
| `file` | str | Source file path |
| `deceased_full_name` | str \| null | Full name of deceased |
| `date_of_birth` | str \| null | Date of birth (as printed) |
| `date_of_death` | str \| null | Date of death (as printed) |
| `ssn_last4` | str \| null | Last 4 digits of SSN |
| `cause_of_death` | str \| null | Cause of death |
| `county` | str \| null | County of death |
| `state` | str \| null | State of death |
| `surviving_spouse` | str \| null | Surviving spouse name |
| `filer_relationship` | str \| null | Relationship of filer to deceased |
| `confidence` | float | Model confidence score (0.0–1.0) |

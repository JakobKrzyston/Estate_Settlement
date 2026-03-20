# Estate Settlement

Full-stack application that extracts structured fields from death certificate PDFs using Anthropic's vision API and generates notification letters for 15 institution types (SSA, Medicare, IRS, banks, insurance, utilities, and more).

## Architecture

- **Backend** — Python / FastAPI. Parses death certificate PDFs via Anthropic's vision API, renders notification letters from Jinja2 HTML templates, and exports to PDF or DOCX.
- **Frontend** — React 19 + Vite + Tailwind CSS v4. Upload flow, extracted-field review and editing, institution selection, letter preview, and download.

## Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- An [Anthropic API key](https://console.anthropic.com/settings/keys)

### Environment

Copy the example env file and add your API key:

```bash
cp .env.example .env
# edit .env and set ANTHROPIC_API_KEY
```

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Running

### Development

```bash
# Terminal 1 — backend (from backend/)
uvicorn main:app --reload

# Terminal 2 — frontend (from frontend/)
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Docker

```bash
docker compose up --build
```

The app is served at [http://localhost](http://localhost) (port 80). See [docker-compose.yml](docker-compose.yml) for details.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/parse` | Upload a PDF or image, returns extracted certificate fields |
| POST | `/generate` | Accept fields + institution list, returns rendered HTML letters |
| POST | `/export-pdf` | Render a single letter as a PDF download |
| POST | `/export-docx` | Render a single letter as a DOCX download |

## CLI Tools

The backend also exposes CLI entry points for batch processing and evaluation:

```bash
cd backend

# Extract fields from all sample PDFs → output/results.jsonl
python -m doc_parser.extract

# Extract from specific files
python -m doc_parser.extract samples/TX_Reyes.pdf

# Run evaluation against ground truth
python -m doc_parser.eval

# Run pytest eval harness
pytest tests/test_eval.py -v
```

## Project Structure

```
backend/
  main.py                FastAPI app (API endpoints)
  doc_parser/
    extract.py           Extraction pipeline + Pydantic schema
    generate.py          Letter rendering (Jinja2 templates → HTML/PDF/DOCX)
    eval.py              Evaluation harness (ground truth scoring)
    metrics.py           Cost projection + trial logging
    prompts.py           Prompt constants
  templates/             Jinja2 letter templates (15 institutions)
  tests/test_eval.py     Pytest eval harness with fuzzy scoring
  samples/               Test PDFs + ground_truth.json (gitignored)
  output/                Generated results (gitignored)
frontend/
  src/App.jsx            Main application component
  src/index.css          Tailwind theme config
  vite.config.js         Vite config with API proxy
  package.json           Dependencies
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Anthropic API key |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `EXTRACTION_MODEL` | `claude-sonnet-4-6` | Model for certificate extraction |
| `VITE_BACKEND_URL` | `http://localhost:8000` | Backend URL for Vite dev proxy |

## Output Format

### Generated Letters (PDF / DOCX)

For each institution selected, the app generates a personalized notification letter pre-filled with the deceased's name, dates, SSN last 4, and the filer's information. Letters can be downloaded individually as **PDF** or **DOCX** directly from the browser.

Supported institutions: SSA, Medicare, IRS, bank, credit union, brokerage, mortgage, life insurance, pension, USAA, Amazon, LinkedIn, subscriptions, telecom, utility.

### CLI Extraction Output

Each line of `output/results.jsonl` is a JSON object:

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

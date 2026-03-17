import json
from datetime import date
from pathlib import Path

METRICS_DIR = Path(__file__).parent.parent / "metrics"

# Projected cost per token (USD) — update as Anthropic adjusts list pricing
_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6":         {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
    "claude-opus-4-6":           {"input": 15.00 / 1_000_000, "output": 75.00 / 1_000_000},
    "claude-haiku-4-5-20251001": {"input": 0.80 / 1_000_000, "output": 4.00 / 1_000_000},
}


def projected_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return projected USD cost for a single API call."""
    p = _PRICING.get(model, {"input": 0.0, "output": 0.0})
    return round(p["input"] * input_tokens + p["output"] * output_tokens, 8)


def _today_path() -> Path:
    METRICS_DIR.mkdir(exist_ok=True)
    return METRICS_DIR / f"metrics_{date.today()}.json"


def append_trial(trial: dict) -> Path:
    """Append a trial dict to today's metrics file. Returns the file path."""
    path = _today_path()
    records = json.loads(path.read_text()) if path.exists() else []
    records.append(trial)
    path.write_text(json.dumps(records, indent=2))
    return path

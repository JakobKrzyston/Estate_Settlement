"""Evaluation harness: runs extraction on sample PDFs and scores results against ground_truth.json."""

import uuid
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Ground truth
# ---------------------------------------------------------------------------
# Keys match Path(image_path).name as passed to parse_certificate().
# Only fields extractable from the TX mail application form are included;
# cause_of_death and surviving_spouse are absent from that form and therefore
# omitted here so they don't unfairly penalise the score.

GROUND_TRUTH = {
    "TX_Thornton.pdf": {
        "deceased_full_name": "Robert James Thornton",
        "date_of_birth": "1941-07-22",
        "date_of_death": "2026-03-14",
        "ssn_last4": "2310",
        "county": "Harris",
        "state": "TX",
        "filer_relationship": "Child",
    },
    "TX_Reyes.pdf": {
        "deceased_full_name": "Maria Elena Reyes",
        "date_of_birth": "1958-03-15",
        "date_of_death": "2023-11-02",
        "ssn_last4": "8821",
        "county": "Bexar",
        "state": "TX",
        "filer_relationship": "Spouse",
    },
    "TX_Whitfield.pdf": {
        "deceased_full_name": "Kevin Dale Whitfield",
        "date_of_birth": "1985-09-04",
        "date_of_death": "2022-06-28",
        "ssn_last4": "4401",
        "county": "Dallas",
        "state": "TX",
        "filer_relationship": "Parent",
    },
}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score(extracted: dict, truth: dict) -> float:
    """Return fraction of truth fields matched exactly in extracted (0.0–1.0).

    'confidence' is excluded from scoring.
    """
    fields = [k for k in truth if k != "confidence"]
    hits = sum(1 for f in fields if extracted.get(f) == truth[f])
    return hits / len(fields)


# ---------------------------------------------------------------------------
# CLI eval harness
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from doc_parser.extract import _parse_certificate_with_metrics
    from doc_parser import metrics

    samples_dir = Path(__file__).parent.parent / "samples"

    trial_files = []
    scores = []

    for filename, truth in GROUND_TRUTH.items():
        pdf_path = samples_dir / filename
        try:
            m = _parse_certificate_with_metrics(str(pdf_path))
        except Exception as exc:
            print(f"{filename}: ERROR — {exc}")
            continue

        extracted = m["result"]
        s = score(extracted, truth)
        scores.append(s)

        fields = [k for k in truth if k != "confidence"]
        hits = int(s * len(fields))

        field_results = {
            f: {
                "expected": truth[f],
                "got": extracted.get(f),
                "match": extracted.get(f) == truth[f],
            }
            for f in fields
        }

        cost = metrics.projected_cost(m["model"], m["input_tokens"], m["output_tokens"])

        trial_files.append({
            "filename": filename,
            "model": m["model"],
            "latency_ms": m["latency_ms"],
            "input_tokens": m["input_tokens"],
            "output_tokens": m["output_tokens"],
            "projected_cost_usd": cost,
            "accuracy": round(s, 6),
            "fields_correct": hits,
            "fields_total": len(fields),
            "model_confidence": extracted.get("confidence"),
            "field_results": field_results,
        })

        # stdout — same format as before
        print(f"{filename}: {s:.0%}  ({hits}/{len(fields)} fields)")
        for field in fields:
            got = extracted.get(field)
            tag = "OK" if got == truth[field] else "FAIL"
            print(f"  {tag}  {field}: expected={truth[field]!r}  got={got!r}")

    if scores:
        overall = sum(scores) / len(scores)
        print(f"\nOverall: {overall:.0%}  ({len(scores)} files)")

        total_input   = sum(f["input_tokens"]      for f in trial_files)
        total_output  = sum(f["output_tokens"]     for f in trial_files)
        total_cost    = sum(f["projected_cost_usd"] for f in trial_files)
        total_correct = sum(f["fields_correct"]    for f in trial_files)
        total_fields  = sum(f["fields_total"]      for f in trial_files)
        model = trial_files[0]["model"]

        trial = {
            "trial_id": uuid.uuid4().hex[:8],
            "run_at": datetime.now().isoformat(),
            "model": model,
            "files": trial_files,
            "summary": {
                "files_count": len(trial_files),
                "overall_accuracy": round(overall, 6),
                "fields_correct": total_correct,
                "fields_total": total_fields,
                "total_latency_ms": sum(f["latency_ms"] for f in trial_files),
                "total_input_tokens": total_input,
                "total_output_tokens": total_output,
                "projected_cost_usd": round(total_cost, 8),
            },
        }

        path = metrics.append_trial(trial)
        print(f"Metrics written to: {path}")

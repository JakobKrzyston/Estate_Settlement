"""Evaluation harness: runs extraction on sample PDFs and scores results against ground_truth.json."""

import json
import uuid
from datetime import datetime
from pathlib import Path

_SAMPLES_DIR = Path(__file__).parent.parent / "samples"
_GT_PATH = _SAMPLES_DIR / "ground_truth.json"


# ---------------------------------------------------------------------------
# Date conversion helpers
# ---------------------------------------------------------------------------

def _date_slash_to_iso(value: str) -> str:
    """Convert MM/DD/YYYY to YYYY-MM-DD.

    Args:
        value: Date string in MM/DD/YYYY format.

    Returns:
        ISO-format date string YYYY-MM-DD.
    """
    return datetime.strptime(value, "%m/%d/%Y").strftime("%Y-%m-%d")


def _date_long_to_iso(value: str) -> str:
    """Convert 'Month D, YYYY' to YYYY-MM-DD.

    Args:
        value: Date string such as 'March 3, 1952'.

    Returns:
        ISO-format date string YYYY-MM-DD.
    """
    return datetime.strptime(value, "%B %d, %Y").strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Per-template projection functions
# ---------------------------------------------------------------------------

def _project_texas_mail_application(example: dict) -> dict:
    """Project a texas_mail_application entry to flat CertificateData fields.

    cause_of_death and surviving_spouse are excluded — they do not appear on
    this form type and omitting them avoids unfair scoring penalties.

    Args:
        example: One entry from the template's 'examples' list.

    Returns:
        Dict of flat fields comparable to CertificateData output.
    """
    d = example["decedent"]
    a = example["applicant"]
    return {
        "deceased_full_name": f"{d['first_name']} {d['middle_name']} {d['last_name']}",
        "date_of_birth": _date_slash_to_iso(d["date_of_birth"]),
        "date_of_death": _date_slash_to_iso(d["date_of_death"]),
        "ssn_last4": d["ssn"].replace("-", "")[-4:],
        "county": d["place_of_death_county"],
        "state": a["state"],
        "filer_relationship": a["relationship"],
    }


def _project_georgia_death_certificate(example: dict) -> dict:
    """Project a georgia_death_certificate entry to flat CertificateData fields.

    Args:
        example: One entry from the template's 'examples' list.

    Returns:
        Dict of flat fields comparable to CertificateData output.
    """
    d = example["decedent"]
    return {
        "deceased_full_name": d["legal_full_name"],
        "date_of_birth": _date_slash_to_iso(d["date_of_birth"]),
        "date_of_death": _date_slash_to_iso(d["date_of_death"]),
        "ssn_last4": d["ssn"].replace("-", "")[-4:],
        "county": example["place_of_death"]["county"],
        "state": d["residence"]["state"],
        "filer_relationship": example["informant"]["relationship"],
        "cause_of_death": example["cause_of_death"]["immediate_cause_a"],
        "surviving_spouse": d.get("surviving_spouse"),
    }


def _project_florida_death_certificate_application(example: dict) -> dict:
    """Project a florida_death_certificate_application entry to flat CertificateData fields.

    cause_of_death is excluded — it does not appear on this form type.

    Args:
        example: One entry from the template's 'examples' list.

    Returns:
        Dict of flat fields comparable to CertificateData output.
    """
    ds = example["death_search"]
    # place_of_death_city_county format: "City, <County Name> County"
    county = ds["place_of_death_city_county"].split(", ", 1)[1].rsplit(" County", 1)[0]
    return {
        "deceased_full_name": ds["full_name_on_record"],
        "date_of_birth": _date_slash_to_iso(ds["date_of_birth"]),
        "date_of_death": _date_slash_to_iso(ds["date_of_death"]),
        "ssn_last4": ds["ssn"].replace("-", "")[-4:],
        "county": county,
        "state": example["applicant"]["state"],
        "filer_relationship": example["applicant"]["relationship_to_decedent"],
    }


def _project_cdc_us_standard_certificate_of_death(example: dict) -> dict:
    """Project a cdc_us_standard_certificate_of_death entry to flat CertificateData fields.

    CDC stores dates as 'Month D, YYYY' (e.g. 'March 3, 1952'), not MM/DD/YYYY.

    Args:
        example: One entry from the template's 'examples' list.

    Returns:
        Dict of flat fields comparable to CertificateData output.
    """
    d = example["decedent"]
    mc = example["medical_certification"]
    return {
        "deceased_full_name": d["legal_name"],
        "date_of_birth": _date_long_to_iso(d["date_of_birth"]),
        "date_of_death": _date_long_to_iso(d["date_of_death"]),
        "ssn_last4": d["ssn"].replace("-", "")[-4:],
        "county": example["place_of_death"]["county"],
        "state": d["residence"]["state"],
        "filer_relationship": example["informant"]["relationship"],
        "cause_of_death": mc["cause_of_death"]["part_1"][0]["cause"],
        "surviving_spouse": d.get("surviving_spouse_name"),
    }


def _project_california_court_order_delayed_registration(example: dict) -> dict:
    """Project a california_court_order_delayed_registration entry to flat CertificateData fields.

    surviving_spouse is excluded — the JSON stores it as a nested object
    (first_name / middle_name / last_name_birth), not a plain string, so it
    cannot be compared directly to the model's string output.

    Args:
        example: One entry from the template's 'examples' list.

    Returns:
        Dict of flat fields comparable to CertificateData output.
    """
    d = example["decedent"]
    return {
        "deceased_full_name": f"{d['first_name']} {d['middle_name']} {d['last_name']}",
        "date_of_birth": _date_slash_to_iso(d["date_of_birth"]),
        "date_of_death": _date_slash_to_iso(d["date_of_death"]),
        "ssn_last4": d["ssn"].replace("-", "")[-4:],
        "county": example["place_of_death"]["county"],
        "state": d["residence"]["state"],
        "filer_relationship": d["informant"]["relationship"],
    }


# ---------------------------------------------------------------------------
# Template dispatch table and ground truth loader
# ---------------------------------------------------------------------------

_PROJECTORS: dict[str, object] = {
    "texas_mail_application": _project_texas_mail_application,
    "georgia_death_certificate": _project_georgia_death_certificate,
    "florida_death_certificate_application": _project_florida_death_certificate_application,
    "cdc_us_standard_certificate_of_death": _project_cdc_us_standard_certificate_of_death,
    "california_court_order_delayed_registration": _project_california_court_order_delayed_registration,
}


def _load_ground_truth() -> dict[str, dict]:
    """Load and project ground truth from ground_truth.json.

    Iterates all templates and examples. Any example with a 'pdf_filename'
    field is projected to flat CertificateData fields using the
    template-specific projector. Examples without 'pdf_filename' are skipped.

    To add a new PDF to evaluation: set 'pdf_filename' on the corresponding
    entry in samples/ground_truth.json — no code changes required.

    Returns:
        Dict mapping pdf_filename -> flat truth dict.

    Raises:
        KeyError: If a template name in ground_truth.json has no registered projector.
        FileNotFoundError: If ground_truth.json does not exist.
    """
    raw = json.loads(_GT_PATH.read_text())
    result: dict[str, dict] = {}
    for template_name, template_data in raw["templates"].items():
        project = _PROJECTORS[template_name]
        for example in template_data["examples"]:
            filename = example.get("pdf_filename")
            if not filename:
                continue
            result[filename] = project(example)
    return result


GROUND_TRUTH = _load_ground_truth()


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
    field_hits: dict[str, int] = {}
    field_totals: dict[str, int] = {}

    for pdf_path in sorted(samples_dir.glob("*.pdf")):
        filename = pdf_path.name
        truth = GROUND_TRUTH.get(filename)
        if truth is None:
            print(f"{filename}: no ground truth, skipping")
            continue
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

        for f, r in field_results.items():
            field_totals[f] = field_totals.get(f, 0) + 1
            if r["match"]:
                field_hits[f] = field_hits.get(f, 0) + 1

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

        print(f"\nField-level accuracy:")
        print(f"  {'Field':<25}  {'Correct':>7}  {'Total':>5}  {'Accuracy':>8}")
        print(f"  {'-'*25}  {'-'*7}  {'-'*5}  {'-'*8}")
        for field in sorted(field_totals, key=lambda f: field_hits.get(f, 0) / field_totals[f]):
            h = field_hits.get(field, 0)
            t = field_totals[field]
            print(f"  {field:<25}  {h:>7}  {t:>5}  {h/t:>7.0%}")

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
                "field_accuracy": {
                    f: round(field_hits.get(f, 0) / field_totals[f], 6)
                    for f in field_totals
                },
            },
        }

        path = metrics.append_trial(trial)
        print(f"Metrics written to: {path}")

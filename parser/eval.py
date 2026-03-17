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
    from parser import parse_certificate

    samples_dir = Path(__file__).parent.parent / "samples"
    scores = []

    for filename, truth in GROUND_TRUTH.items():
        pdf_path = samples_dir / filename
        try:
            extracted = parse_certificate(str(pdf_path))
        except Exception as exc:
            print(f"{filename}: ERROR — {exc}")
            continue

        s = score(extracted, truth)
        scores.append(s)
        print(f"{filename}: {s:.0%}  ({int(s * len(truth))}/{len(truth)} fields)")
        for field in truth:
            got = extracted.get(field)
            match = "OK" if got == truth[field] else "FAIL"
            print(f"  {match}  {field}: expected={truth[field]!r}  got={got!r}")

    if scores:
        print(f"\nOverall: {sum(scores)/len(scores):.0%}  ({len(scores)} files)")

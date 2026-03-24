"""Pytest harness for OCR test results: parametrised per-field tests against synthetic ground truth.

Usage:
    python -m ocr_test.evaluate          # populate output/synth_results.jsonl first
    pytest tests/test_ocr.py -v          # run harness
    pytest tests/test_ocr.py -v -s       # include partial-match detail lines
"""

import json
from pathlib import Path

import pytest

from ocr_test.score import _ALL_FIELDS, _levenshtein_ratio, score_field

_RESULTS_PATH = Path(__file__).parent.parent / "output" / "synth_results.jsonl"
_MANIFEST_PATH = Path(__file__).parent.parent / "samples" / "synthetic" / "manifest.json"

# Minimum weighted accuracy across all evaluated samples.
_MIN_WEIGHTED_ACCURACY = 0.5


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_manifest() -> dict[str, dict]:
    """Load manifest keyed by sample_id."""
    if not _MANIFEST_PATH.exists():
        return {}
    with open(_MANIFEST_PATH) as f:
        data = json.load(f)
    return {s["sample_id"]: s for s in data["samples"]}


def _load_results() -> dict[str, dict]:
    """Load cached extraction results keyed by sample_id."""
    if not _RESULTS_PATH.exists():
        return {}
    results: dict[str, dict] = {}
    for line in _RESULTS_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        results[r["sample_id"]] = r
    return results


_MANIFEST = _load_manifest()
_RESULTS = _load_results()


# ---------------------------------------------------------------------------
# Build parametrised test cases
# ---------------------------------------------------------------------------

_TEST_CASES = []
_TEST_IDS = []

for sid, sample in sorted(_MANIFEST.items()):
    if sid not in _RESULTS:
        continue
    for field_name in _ALL_FIELDS:
        expected = sample["fields"].get(field_name, "")
        _TEST_CASES.append((sid, field_name, expected))
        _TEST_IDS.append(f"{sid}::{field_name}")


# ---------------------------------------------------------------------------
# Per-field tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("sample_id,field,expected", _TEST_CASES, ids=_TEST_IDS)
def test_field(sample_id: str, field: str, expected: str) -> None:
    """Assert that a single extracted field scores at least 'partial'.

    Args:
        sample_id: Synthetic sample identifier.
        field: Field name.
        expected: Ground truth value.
    """
    rec = _RESULTS.get(sample_id)
    if rec is None:
        pytest.skip(f"No cached result for {sample_id!r}")

    got = rec["extracted"].get(field, "")
    fr = score_field(field, got, expected)

    if fr.status == "partial":
        print(f"\n  PARTIAL  {field}: expected={expected!r}  got={got!r}  similarity={fr.similarity:.2f}")

    if fr.status == "fail":
        pytest.fail(
            f"Field '{field}' scored fail.\n"
            f"  expected : {expected!r}\n"
            f"  got      : {got!r}"
        )


# ---------------------------------------------------------------------------
# Overall accuracy
# ---------------------------------------------------------------------------

def test_overall_accuracy() -> None:
    """Assert weighted accuracy across all evaluated samples meets minimum threshold."""
    if not _RESULTS or not _MANIFEST:
        pytest.skip("No cached results or manifest — run ocr_test.evaluate first")

    total_weight = 0.0
    max_weight = 0.0

    for sid, rec in _RESULTS.items():
        sample = _MANIFEST.get(sid)
        if sample is None:
            continue
        for field_name in _ALL_FIELDS:
            expected = sample["fields"].get(field_name, "")
            got = rec["extracted"].get(field_name, "")
            fr = score_field(field_name, got, expected)
            if fr.status == "ok":
                total_weight += 1.0
            elif fr.status == "partial":
                total_weight += 0.5
            max_weight += 1.0

    if max_weight == 0:
        pytest.skip("No fields to evaluate")

    accuracy = total_weight / max_weight
    print(f"\n  Overall weighted accuracy: {accuracy:.1%} ({total_weight:.1f}/{max_weight:.0f})")

    assert accuracy >= _MIN_WEIGHTED_ACCURACY, (
        f"Weighted accuracy {accuracy:.1%} is below minimum {_MIN_WEIGHTED_ACCURACY:.0%}"
    )

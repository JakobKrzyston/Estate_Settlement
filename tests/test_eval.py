"""Pytest eval harness: compare parser output to ground truth with fuzzy field scoring.

Scores each extracted field as correct, partially_correct, or wrong.
Levenshtein distance is used for free-text fields so minor formatting
differences (extra spaces, capitalisation variants) do not count as failures.

Usage:
    python -m doc_parser.extract          # populate output/results.jsonl first
    pytest tests/test_eval.py -v          # run harness
    pytest tests/test_eval.py -v -s       # include partial-match detail lines
"""

import json
from pathlib import Path

import pytest

from doc_parser.eval import GROUND_TRUTH, _flatten

_RESULTS_PATH = Path(__file__).parent.parent / "output" / "results.jsonl"

# Free-text fields where Levenshtein fuzzy matching applies.
_FUZZY_FIELDS = frozenset({
    "deceased.full_name",
    "deceased.cause_of_death",
    "deceased.surviving_spouse",
    "deceased.county",
    "filer.name",
    "filer.address",
})

# Levenshtein ratio threshold for "partially_correct" (0–1).
_PARTIAL_THRESHOLD = 0.8

# Scoring weights used in the overall accuracy summary test.
_WEIGHTS = {"correct": 1.0, "partially_correct": 0.5, "wrong": 0.0}

# Minimum weighted accuracy across all evaluated files.
_MIN_WEIGHTED_ACCURACY = 0.5


# ---------------------------------------------------------------------------
# Levenshtein helpers
# ---------------------------------------------------------------------------

def _levenshtein_ratio(a: str, b: str) -> float:
    """Return normalised similarity in [0.0, 1.0]; 1.0 means identical.

    Uses classic Wagner-Fischer DP with O(n) space.

    Args:
        a: First string.
        b: Second string.

    Returns:
        1.0 − edit_distance / max(len(a), len(b)), or 1.0 if both are empty.
    """
    m, n = len(a), len(b)
    if m == 0 and n == 0:
        return 1.0
    if m == 0 or n == 0:
        return 0.0
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        curr = [i] + [0] * n
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = curr
    return 1.0 - prev[n] / max(m, n)


def _score_field(field: str, got, expected) -> str:
    """Return 'correct', 'partially_correct', or 'wrong' for one field.

    Args:
        field: Field name (used to decide exact vs. fuzzy matching).
        got: Value returned by the parser (may be None).
        expected: Ground-truth value (may be None).

    Returns:
        'correct' on exact match; 'partially_correct' if a fuzzy field is
        within the similarity threshold; 'wrong' otherwise.
    """
    if got == expected:
        return "correct"
    if got is None or expected is None:
        return "wrong"
    if field in _FUZZY_FIELDS:
        ratio = _levenshtein_ratio(str(got).lower().strip(), str(expected).lower().strip())
        return "partially_correct" if ratio >= _PARTIAL_THRESHOLD else "wrong"
    return "wrong"


# ---------------------------------------------------------------------------
# Cached result loader
# ---------------------------------------------------------------------------

def _load_cached_results() -> dict[str, dict]:
    """Load extraction results from output/results.jsonl, keyed by basename.

    Returns:
        Dict mapping filename (e.g. 'TX_Thornton.pdf') to extracted field dict.
        Empty dict if the file does not exist.
    """
    if not _RESULTS_PATH.exists():
        return {}
    records: dict[str, dict] = {}
    for line in _RESULTS_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        records[Path(r["file"]).name] = r
    return records


_CACHED = _load_cached_results()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def cached_results() -> dict[str, dict]:
    """Session-scoped fixture exposing the cached extraction results."""
    return _CACHED


# ---------------------------------------------------------------------------
# Per-field parametrised tests
# ---------------------------------------------------------------------------

_FLAT_GROUND_TRUTH = {fn: _flatten(truth) for fn, truth in GROUND_TRUTH.items()}

_TEST_CASES = [
    (filename, field, truth[field])
    for filename, truth in sorted(_FLAT_GROUND_TRUTH.items())
    for field in truth
    if field != "confidence"
]

_TEST_IDS = [f"{fn}::{fld}" for fn, fld, _ in _TEST_CASES]


@pytest.mark.parametrize("filename,field,expected", _TEST_CASES, ids=_TEST_IDS)
def test_field(filename: str, field: str, expected, cached_results: dict) -> None:
    """Assert that a single extracted field scores at least 'partially_correct'.

    Skips if no cached result is available for the file (run
    ``python -m doc_parser.extract`` to generate output/results.jsonl).

    Args:
        filename: PDF basename, e.g. 'TX_Thornton.pdf'.
        field: Dot-notation field name, e.g. 'deceased.full_name'.
        expected: Ground-truth value.
        cached_results: Session fixture with loaded results.jsonl data.
    """
    if filename not in cached_results:
        pytest.skip(
            f"No cached result for {filename!r} — run: python -m doc_parser.extract"
        )

    got = _flatten(cached_results[filename]).get(field)
    category = _score_field(field, got, expected)

    if category == "partially_correct":
        ratio = _levenshtein_ratio(
            str(got).lower().strip(), str(expected).lower().strip()
        )
        print(
            f"\n  PARTIAL  {field}: expected={expected!r}  got={got!r}  "
            f"similarity={ratio:.2f}"
        )

    if category == "wrong":
        pytest.fail(
            f"Field '{field}' scored wrong.\n"
            f"  expected : {expected!r}\n"
            f"  got      : {got!r}"
        )


# ---------------------------------------------------------------------------
# Overall accuracy summary test
# ---------------------------------------------------------------------------

def test_overall_accuracy(cached_results: dict) -> None:
    """Assert weighted accuracy across all evaluated files meets minimum threshold.

    Weighted score: correct=1.0, partially_correct=0.5, wrong=0.0.
    Skips if no files have cached results.

    Args:
        cached_results: Session fixture with loaded results.jsonl data.
    """
    available = {fn: gt for fn, gt in _FLAT_GROUND_TRUTH.items() if fn in cached_results}
    if not available:
        pytest.skip("No cached results — run: python -m doc_parser.extract")

    total_weight = 0.0
    max_weight = 0.0

    for filename, truth in available.items():
        extracted = _flatten(cached_results[filename])
        fields = [f for f in truth if f != "confidence"]
        for field in fields:
            category = _score_field(field, extracted.get(field), truth[field])
            total_weight += _WEIGHTS[category]
            max_weight += 1.0

    weighted_accuracy = total_weight / max_weight
    print(
        f"\n  Overall weighted accuracy: {weighted_accuracy:.1%} "
        f"({total_weight:.1f}/{max_weight:.0f} points, {len(available)} file(s))"
    )

    assert weighted_accuracy >= _MIN_WEIGHTED_ACCURACY, (
        f"Weighted accuracy {weighted_accuracy:.1%} is below minimum "
        f"{_MIN_WEIGHTED_ACCURACY:.0%}"
    )

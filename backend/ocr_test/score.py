"""Scoring engine for OCR test results: field-level comparison with fuzzy matching and diagnostics."""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Field classification
# ---------------------------------------------------------------------------

_EXACT_FIELDS = frozenset({
    "sex", "ssn", "age", "date_of_birth", "date_of_death",
    "marital_status", "manner_of_death", "state_residence", "date_signed",
})

_FUZZY_FIELDS = frozenset({
    "decedent_name", "birthplace", "residence_street", "county_residence",
    "spouse_name", "occupation", "industry", "father_name", "mother_name",
    "cause_a", "cause_b", "place_of_death", "certifier_name",
})

_INTERVAL_FIELDS = frozenset({"cause_a_interval", "cause_b_interval"})

_ALL_FIELDS = sorted(_EXACT_FIELDS | _FUZZY_FIELDS | _INTERVAL_FIELDS)

# Levenshtein similarity threshold for "partial" on fuzzy fields
_PARTIAL_THRESHOLD = 0.8


# ---------------------------------------------------------------------------
# Levenshtein
# ---------------------------------------------------------------------------

def _levenshtein_ratio(a: str, b: str) -> float:
    """Return normalised similarity in [0.0, 1.0]; 1.0 means identical.

    Args:
        a: First string.
        b: Second string.

    Returns:
        Similarity ratio.
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


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FieldResult:
    """Scoring result for a single field."""

    field: str
    expected: str
    got: str
    status: str  # "ok", "partial", "fail"
    similarity: float = 1.0


@dataclass
class SampleResult:
    """Scoring result for one synthetic certificate."""

    sample_id: str
    template_id: str
    degradation: str
    fields: list[FieldResult]
    ok_count: int = 0
    partial_count: int = 0
    fail_count: int = 0

    def __post_init__(self) -> None:
        self.ok_count = sum(1 for f in self.fields if f.status == "ok")
        self.partial_count = sum(1 for f in self.fields if f.status == "partial")
        self.fail_count = sum(1 for f in self.fields if f.status == "fail")


@dataclass
class BatchResult:
    """Aggregate scoring across multiple samples."""

    samples: list[SampleResult]
    by_field: dict[str, dict] = field(default_factory=dict)
    by_degradation: dict[str, dict] = field(default_factory=dict)
    by_template: dict[str, dict] = field(default_factory=dict)
    overall_accuracy: float = 0.0

    def __post_init__(self) -> None:
        self._compute()

    def _compute(self) -> None:
        total_ok = total_partial = total_fail = 0
        field_counts: dict[str, dict[str, int]] = {}
        deg_counts: dict[str, dict[str, int]] = {}
        tmpl_counts: dict[str, dict[str, int]] = {}

        for sr in self.samples:
            for fr in sr.fields:
                # Per-field
                fc = field_counts.setdefault(fr.field, {"ok": 0, "partial": 0, "fail": 0})
                fc[fr.status] += 1
                # Per-degradation
                dc = deg_counts.setdefault(sr.degradation, {"ok": 0, "partial": 0, "fail": 0})
                dc[fr.status] += 1
                # Per-template
                tc = tmpl_counts.setdefault(sr.template_id, {"ok": 0, "partial": 0, "fail": 0})
                tc[fr.status] += 1
                # Totals
                if fr.status == "ok":
                    total_ok += 1
                elif fr.status == "partial":
                    total_partial += 1
                else:
                    total_fail += 1

        total = total_ok + total_partial + total_fail
        self.overall_accuracy = (total_ok + 0.5 * total_partial) / total if total else 0.0

        for name, counts in field_counts.items():
            t = counts["ok"] + counts["partial"] + counts["fail"]
            self.by_field[name] = {**counts, "total": t, "accuracy": (counts["ok"] + 0.5 * counts["partial"]) / t if t else 0.0}

        for name, counts in deg_counts.items():
            t = counts["ok"] + counts["partial"] + counts["fail"]
            self.by_degradation[name] = {**counts, "total": t, "accuracy": (counts["ok"] + 0.5 * counts["partial"]) / t if t else 0.0}

        for name, counts in tmpl_counts.items():
            t = counts["ok"] + counts["partial"] + counts["fail"]
            self.by_template[name] = {**counts, "total": t, "accuracy": (counts["ok"] + 0.5 * counts["partial"]) / t if t else 0.0}


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------

def score_field(field_name: str, got: Optional[str], expected: Optional[str]) -> FieldResult:
    """Score a single field extraction against ground truth.

    Args:
        field_name: Name of the field being scored.
        got: Value returned by extraction (may be None).
        expected: Ground truth value (may be None or empty string).

    Returns:
        FieldResult with status, similarity, and both values.
    """
    got_s = str(got) if got is not None else ""
    exp_s = str(expected) if expected is not None else ""

    # Both empty → ok
    if got_s == "" and exp_s == "":
        return FieldResult(field=field_name, expected=exp_s, got=got_s, status="ok", similarity=1.0)

    # Exact match
    if got_s == exp_s:
        return FieldResult(field=field_name, expected=exp_s, got=got_s, status="ok", similarity=1.0)

    # Interval fields: normalize whitespace then exact match
    if field_name in _INTERVAL_FIELDS:
        if " ".join(got_s.split()).lower() == " ".join(exp_s.split()).lower():
            return FieldResult(field=field_name, expected=exp_s, got=got_s, status="ok", similarity=1.0)
        return FieldResult(field=field_name, expected=exp_s, got=got_s, status="fail", similarity=0.0)

    # Exact fields: case-insensitive comparison
    if field_name in _EXACT_FIELDS:
        if got_s.strip().lower() == exp_s.strip().lower():
            return FieldResult(field=field_name, expected=exp_s, got=got_s, status="ok", similarity=1.0)
        return FieldResult(field=field_name, expected=exp_s, got=got_s, status="fail", similarity=0.0)

    # Fuzzy fields
    ratio = _levenshtein_ratio(got_s.lower().strip(), exp_s.lower().strip())
    if ratio >= 0.99:
        status = "ok"
    elif ratio >= _PARTIAL_THRESHOLD:
        status = "partial"
    else:
        status = "fail"
    return FieldResult(field=field_name, expected=exp_s, got=got_s, status=status, similarity=ratio)


def score_sample(
    extracted: dict,
    truth: dict,
    sample_id: str = "",
    template_id: str = "",
    degradation: str = "",
) -> SampleResult:
    """Score all fields for one sample.

    Args:
        extracted: Dict of field values from the extraction API.
        truth: Dict of ground truth field values.
        sample_id: Identifier for this sample.
        template_id: Which form template was used.
        degradation: Degradation level applied.

    Returns:
        SampleResult with per-field results and counts.
    """
    results = []
    for f in _ALL_FIELDS:
        got = extracted.get(f)
        expected = truth.get(f)
        results.append(score_field(f, got, expected))

    return SampleResult(
        sample_id=sample_id,
        template_id=template_id,
        degradation=degradation,
        fields=results,
    )


def score_batch(sample_results: list[SampleResult]) -> BatchResult:
    """Compute aggregate statistics across multiple scored samples.

    Args:
        sample_results: List of SampleResult from score_sample calls.

    Returns:
        BatchResult with breakdowns by field, degradation, and template.
    """
    return BatchResult(samples=sample_results)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_sample_report(sr: SampleResult) -> str:
    """Format a per-field comparison table for one sample.

    Args:
        sr: Scored sample result.

    Returns:
        Multi-line string with aligned columns.
    """
    rule = "\u2500"
    pad = rule * max(1, 60 - len(sr.sample_id))
    lines = [f"\n{rule}{rule} {sr.sample_id} {pad}"]
    lines.append("  {:<22} {:<30} {:<30} {:<14}".format("Field", "Expected", "Got", "Score"))
    lines.append("  {} {} {} {}".format(rule * 22, rule * 30, rule * 30, rule * 14))
    for fr in sr.fields:
        exp = fr.expected[:28] + "\u2026" if len(fr.expected) > 28 else fr.expected
        got = fr.got[:28] + "\u2026" if len(fr.got) > 28 else fr.got
        if fr.status == "ok":
            tag = "OK"
        elif fr.status == "partial":
            tag = f"PARTIAL ({fr.similarity:.2f})"
        else:
            tag = "FAIL"
        lines.append(f"  {fr.field:<22} {exp:<30} {got:<30} {tag:<14}")
    lines.append(f"  Result: {sr.ok_count} ok, {sr.partial_count} partial, {sr.fail_count} fail "
                 f"(out of {len(sr.fields)})")
    return "\n".join(lines)


def format_batch_summary(br: BatchResult) -> str:
    """Format aggregate accuracy tables.

    Args:
        br: Batch scoring result.

    Returns:
        Multi-line string with per-field, per-degradation, per-template tables.
    """
    rule = "\u2500"
    lines = ["\n" + "=" * 70, "AGGREGATE RESULTS", "=" * 70]
    lines.append(f"\nOverall weighted accuracy: {br.overall_accuracy:.1%}")

    # Per-field (sorted worst to best)
    lines.append("\n{:<22} {:>5} {:>8} {:>5} {:>9}".format("Field", "OK", "Partial", "Fail", "Accuracy"))
    lines.append("{} {} {} {} {}".format(rule * 22, rule * 5, rule * 8, rule * 5, rule * 9))
    for name in sorted(br.by_field, key=lambda n: br.by_field[n]["accuracy"]):
        d = br.by_field[name]
        lines.append(f"{name:<22} {d['ok']:>5} {d['partial']:>8} {d['fail']:>5} {d['accuracy']:>8.1%}")

    # Per-degradation
    lines.append("\n{:<12} {:>5} {:>8} {:>5} {:>9}".format("Degradation", "OK", "Partial", "Fail", "Accuracy"))
    lines.append("{} {} {} {} {}".format(rule * 12, rule * 5, rule * 8, rule * 5, rule * 9))
    for name in sorted(br.by_degradation):
        d = br.by_degradation[name]
        lines.append(f"{name:<12} {d['ok']:>5} {d['partial']:>8} {d['fail']:>5} {d['accuracy']:>8.1%}")

    # Per-template
    lines.append("\n{:<25} {:>5} {:>8} {:>5} {:>9}".format("Template", "OK", "Partial", "Fail", "Accuracy"))
    lines.append("{} {} {} {} {}".format(rule * 25, rule * 5, rule * 8, rule * 5, rule * 9))
    for name in sorted(br.by_template):
        d = br.by_template[name]
        lines.append(f"{name:<25} {d['ok']:>5} {d['partial']:>8} {d['fail']:>5} {d['accuracy']:>8.1%}")

    return "\n".join(lines)


def format_failure_index(sample_results: list[SampleResult]) -> str:
    """List every non-OK field across all samples for targeted debugging.

    Args:
        sample_results: List of scored sample results.

    Returns:
        Multi-line string listing each failure/partial match.
    """
    rule = "\u2500"
    lines = ["\n" + "=" * 70, "FAILURE INDEX", "=" * 70]
    lines.append("{:<40} {:<22} {:<25} {:<25} {}".format("Sample", "Field", "Expected", "Got", "Score"))
    lines.append("{} {} {} {} {}".format(rule * 40, rule * 22, rule * 25, rule * 25, rule * 14))

    failures = []
    for sr in sample_results:
        for fr in sr.fields:
            if fr.status != "ok":
                failures.append((sr.sample_id, fr))

    if not failures:
        lines.append("  No failures!")
        return "\n".join(lines)

    for sample_id, fr in failures:
        exp = fr.expected[:23] + "\u2026" if len(fr.expected) > 23 else fr.expected
        got = fr.got[:23] + "\u2026" if len(fr.got) > 23 else fr.got
        tag = f"PARTIAL ({fr.similarity:.2f})" if fr.status == "partial" else "FAIL"
        lines.append(f"{sample_id:<40} {fr.field:<22} {exp:<25} {got:<25} {tag}")

    lines.append(f"\nTotal: {len(failures)} non-OK fields across {len(sample_results)} samples")
    return "\n".join(lines)

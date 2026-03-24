"""CLI evaluation runner: extract synthetic certificates, score against ground truth, report diagnostics.

Usage:
    python -m ocr_test.evaluate                         # all synthetic samples
    python -m ocr_test.evaluate --limit 5               # first 5 only
    python -m ocr_test.evaluate --degradation heavy      # filter by degradation level
    python -m ocr_test.evaluate --results-only           # score from cache, no API calls
    python -m ocr_test.evaluate --sample <id>            # re-run one sample
    python -m ocr_test.evaluate --failures-only          # re-run previously failed samples
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

from .extract import extract_with_metrics
from .score import (
    format_batch_summary,
    format_failure_index,
    format_sample_report,
    score_batch,
    score_sample,
)

_SAMPLES_DIR = Path(__file__).parent.parent / "samples" / "synthetic"
_RESULTS_PATH = Path(__file__).parent.parent / "output" / "synth_results.jsonl"
_MANIFEST_PATH = _SAMPLES_DIR / "manifest.json"


# ---------------------------------------------------------------------------
# Manifest and result cache helpers
# ---------------------------------------------------------------------------

def _load_manifest() -> list[dict]:
    """Load the synthetic data manifest.

    Returns:
        List of sample dicts from manifest.json.

    Raises:
        SystemExit: If manifest.json does not exist.
    """
    if not _MANIFEST_PATH.exists():
        sys.exit(
            f"No manifest found at {_MANIFEST_PATH}\n"
            "Run: python -m ocr_test.synth  to generate synthetic data first."
        )
    with open(_MANIFEST_PATH) as f:
        return json.load(f)["samples"]


def _load_cached_results() -> dict[str, dict]:
    """Load cached extraction results keyed by sample_id.

    Returns:
        Dict mapping sample_id -> cached result record.
    """
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


def _save_cached_results(results: dict[str, dict]) -> None:
    """Write all cached results back to the JSONL file.

    Args:
        results: Dict mapping sample_id -> result record.
    """
    _RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_RESULTS_PATH, "w") as f:
        for r in results.values():
            f.write(json.dumps(r) + "\n")


def _extract_sample(sample: dict) -> dict:
    """Run extraction on one synthetic sample and return a result record.

    Args:
        sample: Sample dict from the manifest.

    Returns:
        Result dict with sample_id, extracted fields, and metrics.
    """
    image_path = _SAMPLES_DIR / sample["image_filename"]
    m = extract_with_metrics(str(image_path))
    return {
        "sample_id": sample["sample_id"],
        "template_id": sample["template_id"],
        "degradation": sample["degradation"],
        "extracted": m["result"],
        "model": m["model"],
        "input_tokens": m["input_tokens"],
        "output_tokens": m["output_tokens"],
        "latency_ms": m["latency_ms"],
        "extracted_at": datetime.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the evaluation pipeline."""
    ap = argparse.ArgumentParser(description="Evaluate OCR extraction on synthetic certificates.")
    ap.add_argument("--limit", type=int, default=None, help="Max samples to process")
    ap.add_argument("--degradation", choices=["light", "medium", "heavy"], default=None,
                    help="Filter to one degradation level")
    ap.add_argument("--results-only", action="store_true",
                    help="Score from cached results only, no API calls")
    ap.add_argument("--sample", type=str, default=None,
                    help="Re-run a single sample by sample_id")
    ap.add_argument("--failures-only", action="store_true",
                    help="Re-run only samples with previous failures")
    args = ap.parse_args()

    manifest_samples = _load_manifest()
    cached = _load_cached_results()

    # Determine which samples to process
    if args.sample:
        targets = [s for s in manifest_samples if s["sample_id"] == args.sample]
        if not targets:
            sys.exit(f"Sample '{args.sample}' not found in manifest.")
    else:
        targets = manifest_samples
        if args.degradation:
            targets = [s for s in targets if s["degradation"] == args.degradation]

    if args.limit and not args.sample:
        targets = targets[:args.limit]

    # If --failures-only, filter to samples that had non-OK fields last run
    if args.failures_only:
        failed_ids = set()
        for sid, rec in cached.items():
            gt_sample = next((s for s in manifest_samples if s["sample_id"] == sid), None)
            if gt_sample is None:
                continue
            sr = score_sample(rec["extracted"], gt_sample["fields"],
                              sid, rec.get("template_id", ""), rec.get("degradation", ""))
            if sr.fail_count > 0 or sr.partial_count > 0:
                failed_ids.add(sid)
        targets = [s for s in targets if s["sample_id"] in failed_ids]
        print(f"Re-running {len(targets)} previously failed/partial samples", file=sys.stderr)

    if not targets:
        sys.exit("No samples to evaluate.")

    # Extract (or use cache)
    for sample in targets:
        sid = sample["sample_id"]
        if args.results_only:
            if sid not in cached:
                print(f"  SKIP {sid} (no cached result)", file=sys.stderr)
            continue

        print(f"  Extracting {sid}...", file=sys.stderr)
        try:
            result = _extract_sample(sample)
            cached[sid] = result
        except Exception as exc:
            print(f"  ERROR {sid}: {exc}", file=sys.stderr)
            continue

    _save_cached_results(cached)

    # Score all targets that have results
    sample_results = []
    for sample in targets:
        sid = sample["sample_id"]
        if sid not in cached:
            continue
        rec = cached[sid]
        sr = score_sample(
            rec["extracted"],
            sample["fields"],
            sample_id=sid,
            template_id=sample["template_id"],
            degradation=sample["degradation"],
        )
        sample_results.append(sr)
        print(format_sample_report(sr))

    if not sample_results:
        sys.exit("No results to score.")

    # Aggregate reports
    br = score_batch(sample_results)
    print(format_batch_summary(br))
    print(format_failure_index(sample_results))

    # Log trial to metrics
    try:
        from doc_parser import metrics
        trial = {
            "trial_id": uuid.uuid4().hex[:8],
            "run_at": datetime.now().isoformat(),
            "pipeline": "ocr_test",
            "model": cached[targets[0]["sample_id"]].get("model", "unknown"),
            "summary": {
                "samples_count": len(sample_results),
                "overall_accuracy": round(br.overall_accuracy, 6),
                "by_degradation": {k: round(v["accuracy"], 6) for k, v in br.by_degradation.items()},
            },
        }
        path = metrics.append_trial(trial)
        print(f"\nMetrics written to: {path}", file=sys.stderr)
    except ImportError:
        pass


if __name__ == "__main__":
    main()

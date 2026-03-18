"""Letter generator: fill death-notification templates from extracted certificate data.

Public API: render_letter, export_pdf, fill_template, generate_letters
CLI: python -m doc_parser.generate
"""

import json
import sys
from pathlib import Path
from typing import Optional

from jinja2 import DebugUndefined, Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "death-notification-templates"
_ALL_TEMPLATES = ["ssa", "medicare", "utility", "telecom", "bank"]

_RENDER_ENV = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent.parent / "templates")),
    keep_trailing_newline=True,
)


def render_letter(institution: str, data: dict) -> str:
    """Render an institution letter template with extracted certificate data.

    Args:
        institution: Template name without extension (e.g. 'ssa', 'bank').
        data: Dict of template variable names → values.

    Returns:
        Rendered letter as a string.
    """
    template = _RENDER_ENV.get_template(f"{institution}.html")
    return template.render(**data)


def export_pdf(html_string: str, output_path: str) -> None:
    """Write a rendered HTML string to a PDF file via WeasyPrint.

    Args:
        html_string: Fully rendered HTML content.
        output_path: Destination file path (e.g. 'output/letters/cert_ssa.pdf').

    Returns:
        None
    """
    from weasyprint import HTML
    HTML(string=html_string).write_pdf(output_path)


def _make_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=DebugUndefined,  # leave unresolved {{ slots }} visible in output
        keep_trailing_newline=True,
    )


def _cert_to_vars(cert: dict) -> dict:
    """Map CertificateData fields to template variable names.

    Args:
        cert: dict returned by parse_certificate() or a JSONL record.

    Returns:
        dict of template variable names → values.
    """
    return {
        "deceased_full_name": cert.get("deceased_full_name") or "",
        "date_of_death": cert.get("date_of_death") or "",
        "date_of_birth": cert.get("date_of_birth") or "",
        "ssn_last4": cert.get("ssn_last4") or "",
        "county": cert.get("county") or "",
        "state": cert.get("state") or "",
        "surviving_spouse": cert.get("surviving_spouse") or "",
        # filer_relationship from cert pre-fills sender_relationship slot
        "sender_relationship": cert.get("filer_relationship") or "",
    }


def fill_template(template_name: str, vars: dict) -> str:
    """Render a named letter template with the given variables.

    Args:
        template_name: One of 'ssa', 'medicare', 'utility', 'telecom', 'bank'
                       (with or without '.txt' extension).
        vars: Dict of variable names → values. Unresolved slots remain visible.

    Returns:
        Rendered letter as a string.

    Raises:
        ValueError: If the template name is not recognised.
        FileNotFoundError: If the templates directory is missing.
    """
    name = template_name.removesuffix(".txt")
    if name not in _ALL_TEMPLATES:
        raise ValueError(f"Unknown template {template_name!r}. Choose from: {_ALL_TEMPLATES}")
    if not _TEMPLATES_DIR.exists():
        raise FileNotFoundError(f"Templates directory not found: {_TEMPLATES_DIR}")

    env = _make_env()
    tmpl = env.get_template(f"{name}.txt")
    return tmpl.render(**vars)


def generate_letters(
    cert: dict,
    supplemental: dict,
    templates: Optional[list[str]] = None,
    output_dir: str = "output/letters",
) -> list[Path]:
    """Fill one or more templates from certificate data and write output files.

    Args:
        cert: Extracted certificate record (from parse_certificate or JSONL).
        supplemental: Additional vars (sender info, account numbers, etc.) that
                      overlay/extend the certificate fields.
        templates: List of template names to render. Defaults to all five.
        output_dir: Directory to write filled letters into.

    Returns:
        List of Paths to written output files.
    """
    names = templates or _ALL_TEMPLATES
    vars = {**_cert_to_vars(cert), **supplemental}

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    written = []
    for name in names:
        text = fill_template(name, vars)
        stem = cert.get("file", "cert")
        stem = Path(stem).stem  # e.g. "TX_Reyes"
        dest = out / f"{stem}_{name}.txt"
        dest.write_text(text)
        written.append(dest)

    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="Fill death-notification letter templates from extracted certificate data."
    )
    ap.add_argument(
        "--results",
        default="output/results.jsonl",
        help="JSONL file produced by doc_parser.extract (default: output/results.jsonl)",
    )
    ap.add_argument(
        "--record",
        type=int,
        default=0,
        help="0-indexed line in the JSONL file to use (default: 0)",
    )
    ap.add_argument(
        "--template",
        choices=_ALL_TEMPLATES,
        help="Single template to render. Omit to use --all.",
    )
    ap.add_argument(
        "--all",
        dest="all_templates",
        action="store_true",
        help="Render all five templates.",
    )
    ap.add_argument(
        "--vars",
        help="Path to a JSON file with supplemental variables (sender info, account numbers, etc.)",
    )
    ap.add_argument(
        "--output",
        default="output/letters",
        help="Output directory (default: output/letters)",
    )
    args = ap.parse_args()

    if not args.template and not args.all_templates:
        ap.error("Specify --template <name> or --all.")

    results_path = Path(args.results)
    if not results_path.exists():
        sys.exit(f"Results file not found: {results_path}")

    lines = results_path.read_text().splitlines()
    if args.record >= len(lines):
        sys.exit(f"Record {args.record} out of range — file has {len(lines)} record(s).")
    cert = json.loads(lines[args.record])

    supplemental: dict = {}
    if args.vars:
        vars_path = Path(args.vars)
        if not vars_path.exists():
            sys.exit(f"Vars file not found: {vars_path}")
        supplemental = json.loads(vars_path.read_text())

    templates = _ALL_TEMPLATES if args.all_templates else [args.template]

    written = generate_letters(cert, supplemental, templates=templates, output_dir=args.output)
    for path in written:
        print(f"✓ {path}", file=sys.stderr)
    print(f"{len(written)} letter(s) written to {args.output}")

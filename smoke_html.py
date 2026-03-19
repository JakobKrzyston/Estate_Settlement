"""Smoke-test all 10 new HTML letter templates against a single vars file."""

import json
from pathlib import Path
from doc_parser.generate import render_letter

TEMPLATES = [
    "amazon", "brokerage", "credit_union", "irs",
    "life_insurance", "linkedin", "mortgage",
    "pension", "subscriptions", "usaa",
]

vars_path = Path("samples/smoke_vars_html.json")
out_dir = Path("output/letters/smoke")
out_dir.mkdir(parents=True, exist_ok=True)

data = json.loads(vars_path.read_text())

for name in TEMPLATES:
    html = render_letter(name, data)
    dest = out_dir / f"{name}.html"
    dest.write_text(html)
    print(f"✓ {dest}")

print(f"\n{len(TEMPLATES)} files written to {out_dir}")

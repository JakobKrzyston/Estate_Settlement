"""Generate synthetic death certificate images with ground truth for OCR testing.

Renders handwriting-style text onto form templates, applies scan degradation,
and emits paired PNG images + a manifest.json with field-level ground truth.

Usage:
    python -m ocr_test.synth --count 20 --seed 42
"""

import argparse
import json
import math
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "samples" / "synthetic"

# ---------------------------------------------------------------------------
# State abbreviations (GT stores two-letter codes to match extraction output)
# ---------------------------------------------------------------------------

_STATES: dict[str, str] = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Florida": "FL", "Georgia": "GA",
    "Illinois": "IL", "Indiana": "IN", "Louisiana": "LA", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Missouri": "MO",
    "Nevada": "NV", "New Jersey": "NJ", "New York": "NY", "North Carolina": "NC",
    "Ohio": "OH", "Oregon": "OR", "Pennsylvania": "PA", "South Carolina": "SC",
    "Tennessee": "TN", "Texas": "TX", "Virginia": "VA", "Washington": "WA",
    "Wisconsin": "WI",
}

_STATE_NAMES = list(_STATES.keys())

# ---------------------------------------------------------------------------
# Name / data pools
# ---------------------------------------------------------------------------

_FIRST_M = [
    "James", "Robert", "John", "Michael", "David", "William", "Richard",
    "Joseph", "Thomas", "Charles", "Daniel", "Carlos", "Jose", "Ahmed",
    "Wei", "Hiroshi", "Raj", "Vladimir", "Patrick", "Marcus",
]
_FIRST_F = [
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Susan", "Dorothy",
    "Karen", "Maria", "Rosa", "Mei", "Yuki", "Priya", "Olga", "Fatima",
    "Carmen", "Helen", "Betty", "Margaret", "Ruth",
]
_LAST = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Martinez",
    "Davis", "Rodriguez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore",
    "Jackson", "White", "Harris", "Martin", "Thompson", "Robinson",
    "Patel", "Kim", "Nguyen", "Chen", "O'Brien", "Mueller", "Kowalski",
    "Boudreaux", "Hernandez", "Washington",
]
_CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
    "San Antonio", "San Diego", "Dallas", "Atlanta", "Miami", "Seattle",
    "Denver", "Boston", "Nashville", "Portland", "Memphis", "Detroit",
    "Minneapolis", "Las Vegas", "Indianapolis", "Columbus", "Charlotte",
]
_OCCUPATIONS = [
    "Teacher", "Nurse", "Truck Driver", "Farmer", "Electrician", "Mechanic",
    "Engineer", "Accountant", "Pharmacist", "Homemaker", "Construction Worker",
    "Secretary", "Retail Clerk", "Restaurant Manager", "Postal Worker",
    "Social Worker", "Taxi Driver", "Plumber", "Retired", "Police Officer",
]
_INDUSTRIES = [
    "Education", "Healthcare", "Transportation", "Agriculture", "Construction",
    "Manufacturing", "Finance", "Retail", "Government", "Technology",
    "Food Service", "Law Enforcement", "Utilities", "Mining",
]
_CAUSES = [
    ("Acute myocardial infarction", "Coronary artery disease", "Hours", "10 years"),
    ("Metastatic lung cancer", "Non-small cell carcinoma", "6 months", "18 months"),
    ("Cerebrovascular accident", "Hypertension", "3 days", "15 years"),
    ("Pneumonia", "COPD", "2 weeks", "10 years"),
    ("Congestive heart failure", "Atrial fibrillation", "3 years", "8 years"),
    ("Sepsis", "Urinary tract infection", "1 week", "3 weeks"),
    ("Pulmonary embolism", "Deep vein thrombosis", "Hours", "2 weeks"),
    ("Alzheimer's disease", "", "7 years", ""),
    ("End-stage renal disease", "Type 2 diabetes mellitus", "2 years", "20 years"),
    ("Hepatocellular carcinoma", "Chronic hepatitis C", "4 months", "15 years"),
    ("Aspiration pneumonia", "Parkinson's disease", "5 days", "12 years"),
    ("Pancreatic cancer", "Adenocarcinoma", "3 months", "9 months"),
]
_FACILITIES = [
    "General Hospital", "Medical Center", "Memorial Hospital",
    "University Hospital", "Veterans Medical Center", "Community Hospital",
    "Regional Medical Center", "Decedent's Home", "Nursing Home",
    "Hospice Facility",
]
_STREETS = ["Main", "Oak", "Elm", "Maple", "Pine", "Cedar", "Park", "Lake", "Hill"]
_SUFFIXES = ["St", "Ave", "Blvd", "Dr", "Rd", "Ln"]

# ---------------------------------------------------------------------------
# Form templates — field positions on a 1700x2200 (200 DPI letter) canvas
# ---------------------------------------------------------------------------

FORM_TEMPLATES = [
    {
        "id": "us_death_cert_v1",
        "name": "US Standard Death Certificate",
        "page_size": (1700, 2200),
        "fields": {
            "decedent_name":    {"bbox": [80, 160, 800, 200], "type": "text"},
            "sex":              {"bbox": [820, 160, 960, 200], "type": "choice"},
            "date_of_death":    {"bbox": [980, 160, 1200, 200], "type": "date"},
            "ssn":              {"bbox": [80, 220, 400, 260], "type": "ssn"},
            "age":              {"bbox": [420, 220, 540, 260], "type": "number"},
            "date_of_birth":    {"bbox": [560, 220, 800, 260], "type": "date"},
            "birthplace":       {"bbox": [80, 280, 600, 320], "type": "text"},
            "residence_street": {"bbox": [620, 280, 1200, 320], "type": "address"},
            "county_residence": {"bbox": [80, 340, 400, 380], "type": "text"},
            "state_residence":  {"bbox": [420, 340, 700, 380], "type": "state"},
            "marital_status":   {"bbox": [80, 400, 300, 440], "type": "choice"},
            "spouse_name":      {"bbox": [320, 400, 800, 440], "type": "text"},
            "occupation":       {"bbox": [80, 460, 500, 500], "type": "text"},
            "industry":         {"bbox": [520, 460, 900, 500], "type": "text"},
            "father_name":      {"bbox": [80, 520, 700, 560], "type": "text"},
            "mother_name":      {"bbox": [80, 580, 700, 620], "type": "text"},
            "cause_a":          {"bbox": [80, 700, 900, 740], "type": "text"},
            "cause_a_interval": {"bbox": [920, 700, 1200, 740], "type": "text"},
            "cause_b":          {"bbox": [80, 760, 900, 800], "type": "text"},
            "cause_b_interval": {"bbox": [920, 760, 1200, 800], "type": "text"},
            "manner_of_death":  {"bbox": [80, 860, 400, 900], "type": "choice"},
            "place_of_death":   {"bbox": [420, 860, 1000, 900], "type": "text"},
            "certifier_name":   {"bbox": [80, 980, 700, 1020], "type": "text"},
            "date_signed":      {"bbox": [720, 980, 1000, 1020], "type": "date"},
        },
    },
    {
        "id": "us_death_cert_v2",
        "name": "US Death Certificate (Alternate Layout)",
        "page_size": (1700, 2200),
        "fields": {
            "decedent_name":    {"bbox": [60, 180, 850, 225], "type": "text"},
            "sex":              {"bbox": [870, 180, 1020, 225], "type": "choice"},
            "date_of_death":    {"bbox": [1040, 180, 1300, 225], "type": "date"},
            "ssn":              {"bbox": [60, 245, 380, 290], "type": "ssn"},
            "age":              {"bbox": [400, 245, 520, 290], "type": "number"},
            "date_of_birth":    {"bbox": [540, 245, 800, 290], "type": "date"},
            "birthplace":       {"bbox": [820, 245, 1300, 290], "type": "text"},
            "residence_street": {"bbox": [60, 310, 800, 355], "type": "address"},
            "county_residence": {"bbox": [60, 375, 420, 420], "type": "text"},
            "state_residence":  {"bbox": [440, 375, 720, 420], "type": "state"},
            "marital_status":   {"bbox": [740, 375, 1000, 420], "type": "choice"},
            "spouse_name":      {"bbox": [1020, 375, 1600, 420], "type": "text"},
            "father_name":      {"bbox": [60, 440, 700, 485], "type": "text"},
            "mother_name":      {"bbox": [720, 440, 1400, 485], "type": "text"},
            "occupation":       {"bbox": [60, 505, 500, 550], "type": "text"},
            "industry":         {"bbox": [520, 505, 960, 550], "type": "text"},
            "cause_a":          {"bbox": [60, 640, 950, 685], "type": "text"},
            "cause_a_interval": {"bbox": [970, 640, 1300, 685], "type": "text"},
            "cause_b":          {"bbox": [60, 705, 950, 750], "type": "text"},
            "cause_b_interval": {"bbox": [970, 705, 1300, 750], "type": "text"},
            "manner_of_death":  {"bbox": [60, 820, 380, 865], "type": "choice"},
            "place_of_death":   {"bbox": [400, 820, 1050, 865], "type": "text"},
            "certifier_name":   {"bbox": [60, 940, 700, 985], "type": "text"},
            "date_signed":      {"bbox": [720, 940, 1050, 985], "type": "date"},
        },
    },
]

# ---------------------------------------------------------------------------
# Font discovery (macOS + Linux)
# ---------------------------------------------------------------------------

_FONT_DIRS = [
    "/Library/Fonts",
    "/System/Library/Fonts",
    "/System/Library/Fonts/Supplemental",
    os.path.expanduser("~/Library/Fonts"),
    "/usr/share/fonts",
    "/usr/local/share/fonts",
]

_HANDWRITING_KW = ["caveat", "dance", "comic", "indie", "chalkboard", "marker", "noteworthy", "snell"]
_SERIF_KW = ["times", "georgia", "garamond", "palatino", "baskerville", "cochin", "didot"]
# Reliable fallbacks known to render Latin glyphs
_FALLBACK_KW = ["arial", "helvetica", "verdana", "trebuchet"]


def _discover_fonts() -> dict[str, str]:
    """Scan system font directories and return {filename: path} for TrueType/OpenType fonts."""
    fonts: dict[str, str] = {}
    for d in _FONT_DIRS:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                if f.endswith((".ttf", ".otf")) and "mono" not in f.lower():
                    fonts[f] = os.path.join(root, f)
    return fonts


_SYSTEM_FONTS = _discover_fonts()


def _pick_font(size: int = 18) -> Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]:
    """Pick a font, preferring handwriting-like ones, then serif, then safe fallbacks."""
    for keywords in [_HANDWRITING_KW, _SERIF_KW, _FALLBACK_KW]:
        for name, path in _SYSTEM_FONTS.items():
            if any(kw in name.lower() for kw in keywords):
                try:
                    return ImageFont.truetype(path, size)
                except (OSError, IOError):
                    continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Record generation
# ---------------------------------------------------------------------------

def _generate_record() -> dict[str, str]:
    """Generate one synthetic person record with all 24 death certificate fields."""
    is_female = random.random() < 0.5
    first = random.choice(_FIRST_F if is_female else _FIRST_M)
    middle_initial = random.choice("ABCDEFGHJKLMNPRSTVW")
    last = random.choice(_LAST)

    birth_year = random.randint(1920, 1990)
    birth_month = random.randint(1, 12)
    birth_day = random.randint(1, 28)
    death_year = random.randint(max(birth_year + 30, 2018), 2025)
    death_month = random.randint(1, 12)
    death_day = random.randint(1, 28)
    age = death_year - birth_year

    cause = random.choice(_CAUSES)
    state_name = random.choice(_STATE_NAMES)
    state_abbr = _STATES[state_name]
    city = random.choice(_CITIES)

    marital = random.choice(["Married", "Divorced", "Widowed", "Never Married"])
    spouse = ""
    if marital in ("Married", "Widowed"):
        sp_first = random.choice(_FIRST_F if not is_female else _FIRST_M)
        spouse = f"{sp_first} {random.choice('ABCDEFGHJKLM')}. {last}"

    ssn = f"{random.randint(100, 899)}-{random.randint(10, 99)}-{random.randint(1000, 9999)}"

    return {
        "decedent_name": f"{first} {middle_initial}. {last}",
        "sex": "Female" if is_female else "Male",
        "date_of_death": f"{death_month:02d}/{death_day:02d}/{death_year}",
        "ssn": ssn,
        "age": str(age),
        "date_of_birth": f"{birth_month:02d}/{birth_day:02d}/{birth_year}",
        "birthplace": f"{city}, {state_name}",
        "residence_street": f"{random.randint(100, 9999)} {random.choice(_STREETS)} {random.choice(_SUFFIXES)}",
        "county_residence": f"{city} County",
        "state_residence": state_abbr,
        "marital_status": marital,
        "spouse_name": spouse,
        "occupation": random.choice(_OCCUPATIONS),
        "industry": random.choice(_INDUSTRIES),
        "father_name": f"{random.choice(_FIRST_M)} {random.choice('ABCDEFGHJKLM')}. {last}",
        "mother_name": f"{random.choice(_FIRST_F)} {random.choice('ABCDEFGHJKLM')}. {random.choice(_LAST)}",
        "cause_a": cause[0],
        "cause_a_interval": cause[2],
        "cause_b": cause[1],
        "cause_b_interval": cause[3],
        "manner_of_death": random.choice(["Natural", "Natural", "Natural", "Natural", "Accident"]),
        "place_of_death": f"{city} {random.choice(_FACILITIES)}",
        "certifier_name": f"Dr. {random.choice(_FIRST_M + _FIRST_F)} {random.choice(_LAST)}, MD",
        "date_signed": f"{death_month:02d}/{death_day:02d}/{death_year}",
    }


# ---------------------------------------------------------------------------
# Form rendering
# ---------------------------------------------------------------------------

def _draw_form_skeleton(img: Image.Image, template: dict) -> None:
    """Draw the empty form structure: border, headers, section bars, field boxes and labels."""
    draw = ImageDraw.Draw(img)
    w, h = template["page_size"]

    draw.rectangle([30, 30, w - 30, h - 30], outline="black", width=2)

    label_font = _pick_font(14)
    title_font = _pick_font(20)
    draw.text((w // 2 - 150, 40), template["name"].upper(), fill="black", font=title_font)
    draw.text(
        (w // 2 - 200, 70),
        "STATE DEPARTMENT OF HEALTH \u2014 VITAL RECORDS",
        fill="gray",
        font=label_font,
    )

    sections = [
        (140, "DECEDENT INFORMATION"),
        (660, "CAUSE OF DEATH"),
        (830, "MANNER AND CIRCUMSTANCES"),
        (950, "CERTIFICATION"),
    ]
    section_font = _pick_font(12)
    for y_pos, title in sections:
        draw.rectangle([40, y_pos - 18, w - 40, y_pos - 2], fill="#1F2B5E")
        draw.text((45, y_pos - 16), title, fill="white", font=section_font)

    small_font = _pick_font(8)
    for field_name, field_info in template["fields"].items():
        x1, y1, x2, y2 = field_info["bbox"]
        draw.rectangle([x1, y1, x2, y2], outline="#999999", width=1)
        label = field_name.replace("_", " ").upper()
        draw.text((x1 + 2, y1 + 1), label, fill="#666666", font=small_font)


def _render_handwritten_text(draw: ImageDraw.ImageDraw, text: str, bbox: list[int], font_size: int = 16) -> None:
    """Render text with slight baseline wobble and spacing variation to simulate handwriting."""
    if not text:
        return

    x1, y1, x2, y2 = bbox
    font = _pick_font(font_size)

    x = x1 + 4
    y = y1 + (y2 - y1) // 2 + 2

    ink_color = random.choice(["#000033", "#000066", "#1a1a2e", "#000000", "#0a0a3c"])

    for char in text:
        dy = random.randint(-1, 1)
        dx = random.randint(-1, 1)
        if x + 12 > x2 - 4:
            break
        draw.text((x + dx, y + dy), char, fill=ink_color, font=font)
        try:
            char_w = font.getlength(char)
        except AttributeError:
            char_w = font_size * 0.6
        x += char_w + random.uniform(-0.5, 1.0)


def _render_certificate(template: dict, record: dict) -> Image.Image:
    """Render a complete certificate image with form skeleton and filled field values.

    Args:
        template: Form template dict with page_size and fields.
        record: Dict of field name -> value strings from _generate_record().

    Returns:
        PIL Image with the rendered certificate.
    """
    w, h = template["page_size"]
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)

    _draw_form_skeleton(img, template)

    for field_name, field_info in template["fields"].items():
        value = record.get(field_name, "")
        if value:
            font_size = random.randint(14, 18)
            _render_handwritten_text(draw, value, field_info["bbox"], font_size)

    return img


# ---------------------------------------------------------------------------
# Scan degradation (Pillow only, no numpy)
# ---------------------------------------------------------------------------

def _apply_degradation(img: Image.Image, level: str) -> Image.Image:
    """Apply realistic scan degradation to simulate a scanned document.

    Args:
        img: Clean rendered certificate image.
        level: One of 'light', 'medium', 'heavy'.

    Returns:
        Degraded PIL Image.
    """
    if level == "light":
        return img.filter(ImageFilter.GaussianBlur(radius=0.3))

    if level == "medium":
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 0.8)))
        angle = random.uniform(-1.5, 1.5)
        img = img.rotate(angle, fillcolor="white", expand=False)
        # Pixel-level noise via spread
        img = img.effect_spread(2)
        return img

    if level == "heavy":
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.8, 1.5)))
        angle = random.uniform(-3, 3)
        img = img.rotate(angle, fillcolor="white", expand=False)
        img = img.effect_spread(4)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(random.uniform(0.7, 0.9))
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(random.uniform(0.9, 1.05))
        return img

    return img


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_dataset(
    count: int = 20,
    degradation: str = "all",
    seed: Optional[int] = None,
    output_dir: Optional[Path] = None,
) -> Path:
    """Generate synthetic certificate images and a ground truth manifest.

    Args:
        count: Number of samples per template. Total images = count * num_templates.
        degradation: 'light', 'medium', 'heavy', or 'all' (cycles through levels).
        seed: Random seed for reproducibility.
        output_dir: Where to write images and manifest.json.

    Returns:
        Path to the generated manifest.json.
    """
    if seed is not None:
        random.seed(seed)

    out = output_dir or _DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    deg_levels = ["light", "medium", "heavy"] if degradation == "all" else [degradation]
    samples: list[dict] = []
    total = 0

    for template in FORM_TEMPLATES:
        for i in range(count):
            deg = deg_levels[i % len(deg_levels)]
            sample_id = f"{template['id']}_{i:04d}_{deg}"

            record = _generate_record()
            img = _render_certificate(template, record)
            img = _apply_degradation(img, deg)

            img_filename = f"{sample_id}.png"
            img.save(str(out / img_filename), "PNG")

            samples.append({
                "sample_id": sample_id,
                "image_filename": img_filename,
                "template_id": template["id"],
                "degradation": deg,
                "fields": record,
            })

            total += 1
            if total % 5 == 0:
                print(f"  Generated {total} samples...", file=sys.stderr)

    manifest_path = out / "manifest.json"
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "sample_count": len(samples),
        "samples": samples,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"Done! {len(samples)} samples written to {out}", file=sys.stderr)
    return manifest_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate synthetic death certificate test data.")
    ap.add_argument("--count", type=int, default=20, help="Samples per template (default: 20)")
    ap.add_argument(
        "--degradation",
        choices=["light", "medium", "heavy", "all"],
        default="all",
        help="Degradation level (default: all)",
    )
    ap.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    ap.add_argument("--output-dir", type=Path, default=None, help="Output directory")
    args = ap.parse_args()

    manifest = generate_dataset(
        count=args.count,
        degradation=args.degradation,
        seed=args.seed,
        output_dir=args.output_dir,
    )
    print(f"Manifest: {manifest}")

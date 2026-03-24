# OCR Pipeline Tuning: Dataset Guide

## The Core Idea

You don't need to find 30 real death certificates with perfect answer keys. Instead, you can tune your extraction pipeline using **publicly available handwritten-form datasets that already have ground truth**, then transfer that capability to death certificates.

The OCR pipeline has two separable problems: (1) reading handwritten text from noisy scans, and (2) understanding which field each piece of text belongs to. Different datasets target each skill.

---

## Tier 1: Datasets That Directly Apply (forms + ground truth)

### FUNSD — Form Understanding in Noisy Scanned Documents

**What it is:** 199 real scanned business forms (tobacco industry documents from the 1980s-90s) with full annotations: every word has a bounding box, text transcription, and semantic label (header / question / answer) plus entity linking between field labels and values.

**Why it fits:** These are *real scans* of *real forms* — noisy, skewed, faded, with mixed typed and handwritten entries. The question-answer linking is exactly the same task as "which field does this text belong to?" on a death certificate.

**Format:** PNG images + JSON annotations with word-level bounding boxes and text.

**Get it:**
- Original (199 docs): https://guillaumejaume.github.io/FUNSD/
- FUNSD+ (1,113 docs, revised annotations): https://huggingface.co/datasets/konfuzio/funsd_plus
- On Kaggle: https://www.kaggle.com/datasets/aravindram11/funsdform-understanding-noisy-scanned-documents

**License:** Non-commercial, research, and educational use.

**How to use it for your pipeline:**
1. Train/validate your OCR text detection on the word-level bounding boxes
2. Train/validate your field-value association on the entity linking annotations
3. Measure precision/recall on the "answer" entities — these map to your "filled field values"

---

### NIST Special Database 6 — Handwritten Tax Forms

**What it is:** 5,595 images of IRS 1040 tax forms filled out with synthesized handwriting from 2,100 real writers. Each form image comes with an ASCII "answer file" containing the ground truth value for every entry field.

**Why it fits:** This is the closest public analog to "handwritten death certificates with answer keys." Structured government forms, defined field regions, handprinted data, with a per-field ground truth file. The forms even have similar complexity (names, numbers, dates, addresses).

**Format:** Binary TIFF images + ASCII reference files (one per form, listing field ID → value).

**Get it:** https://www.nist.gov/srd/nist-special-database-6

**License:** NIST open data, free for research and development.

**How to use it for your pipeline:**
1. Use the field-level answer files as ground truth for end-to-end extraction accuracy
2. The 20 different form faces test your pipeline's ability to handle layout variation
3. Measure character-level and field-level accuracy separately

---

### NIST Special Database 2 — Machine-Printed Tax Forms

**What it is:** 5,590 IRS 1040 forms with machine-printed (typed) entries and per-field ASCII ground truth. Same structure as SD6 but typed instead of handwritten.

**Why it fits:** Tests your pipeline on the typed-form case (many modern death certificates are typed, not handwritten). Same form templates as SD6, so you can directly compare handwritten vs. typed accuracy.

**Get it:** https://www.nist.gov/srd/nist-special-database-2

---

### XFUND — Multilingual Form Understanding

**What it is:** Human-annotated forms in 7 languages (Chinese, Japanese, Spanish, French, Italian, German, Portuguese) with key-value pair labels. Each form image has OCR text, bounding boxes, and semantic entity annotations.

**Why it fits:** If you need to handle foreign/international death certificates, this is the only public dataset with multilingual form understanding ground truth.

**Format:** JSON annotations with word boxes, entity labels, and relations + form images.

**Get it:** https://github.com/doc-analysis/XFUND/releases/tag/v1.0

**License:** CC-BY 4.0.

---

## Tier 2: Datasets for OCR Sub-Skills

### NIST Special Database 19 — Handprinted Characters

**What it is:** 810,000 character images from 3,600 writers, with ground truth labels. Full-page form images plus isolated character crops.

**Why it fits:** If your OCR struggles with specific characters (e.g., confusing "1" and "7", "0" and "O"), this dataset lets you measure and improve character-level recognition.

**Get it:** https://www.nist.gov/srd/nist-special-database-19

### IAM Handwriting Database

**What it is:** 13,353 handwritten English text line images from 657 writers, with full transcriptions.

**Why it fits:** Trains the "read this handwritten line" step of your pipeline. Not form-structured, but excellent for raw handwriting recognition.

**Get it:** https://fki.tic.heia-fr.ch/databases/iam-handwriting-database (registration required)

---

## Tier 3: Your Synthetic Generator (included)

The `synth.py` module in this directory generates unlimited paired training data:

**What it produces:**
- PNG images of death certificate forms with simulated handwritten field values
- JSON ground truth manifest with exact text, bounding boxes, and field types for every field

**Three degradation levels:**
- `light` — clean rendering, slight blur
- `medium` — blur + skew (±1.5°) + pixel spread
- `heavy` — heavy blur + skew (±3°) + spread + contrast reduction

**How to scale it:**
```bash
cd backend
python -m ocr_test.synth --count 500  # 500 per template = 1,000 total samples
```

**Limitations (be honest with yourself):**
- The "handwriting" is font-rendered with wobble, not actual handwriting strokes
- The form templates are simplified compared to real state forms
- The degradation is synthetic, not real scanner artifacts
- This is good for testing your *field extraction logic* but will overstate your *OCR accuracy* on real handwritten documents

---

## Recommended Tuning Strategy

### Phase 1: Get the pipeline working (use synthetic data)
1. Generate 200-500 samples with `python -m ocr_test.synth --count 250`
2. Run extraction: `python -m ocr_test.evaluate --limit 20`
3. Measure field-level extraction accuracy
4. Target: >95% on synthetic data before moving on

### Phase 2: Harden OCR on real handwriting (use NIST SD6 + FUNSD)
1. Download NIST SD6 (handwritten tax forms)
2. Run your pipeline on those forms using their answer files as ground truth
3. Your accuracy will drop significantly — this is the real signal
4. Tune OCR parameters (confidence thresholds, preprocessing, model selection)
5. Download FUNSD and test field-association accuracy on real noisy scans

### Phase 3: Test on real death certificates
1. Take your 5 original certificates (TX_Reyes, TX_Thornton, TX_Whitfield + GA samples)
2. Manually create ground truth JSON for each (tedious but only 5 files)
3. Measure accuracy — this is your real benchmark number
4. If accuracy is poor, identify whether the bottleneck is OCR or field association

### Phase 4: Expand coverage
1. For multilingual: add XFUND test samples
2. For character-level debugging: use NIST SD19
3. For typed forms: use NIST SD2
4. Source a few real scanned death certificates from FamilySearch.org and manually transcribe them

---

## Quick Links Summary

| Dataset | Type | Size | Ground Truth | Download |
|---------|------|------|-------------|----------|
| FUNSD | Real scanned forms | 199 docs | Word boxes + entity labels + linking | https://guillaumejaume.github.io/FUNSD/ |
| FUNSD+ | Real scanned forms | 1,113 docs | Same as FUNSD, revised | HuggingFace: konfuzio/funsd_plus |
| NIST SD6 | Handwritten tax forms | 5,595 pages | Per-field ASCII answer files | https://www.nist.gov/srd/nist-special-database-6 |
| NIST SD2 | Typed tax forms | 5,590 pages | Per-field ASCII answer files | https://www.nist.gov/srd/nist-special-database-2 |
| NIST SD19 | Handprinted characters | 810K chars | Character-level labels | https://www.nist.gov/srd/nist-special-database-19 |
| XFUND | Multilingual forms | 7 languages | Key-value annotations | https://github.com/doc-analysis/XFUND |
| IAM | Handwritten text lines | 13,353 lines | Full transcriptions | https://fki.tic.heia-fr.ch/databases/iam-handwriting-database |
| Synthetic (yours) | Generated death certs | Unlimited | JSON manifest with field values | `python -m ocr_test.synth` |

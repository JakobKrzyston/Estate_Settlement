"""Prompt constants for OCR test extraction; covers all 24 death certificate fields."""

EXTRACT_PROMPT = """You are extracting structured data from a US death certificate image.

Return ONLY a valid JSON object with these exact keys:

{
  "decedent_name":    Full legal name (first, middle initial, last) as written,
  "sex":              "Male" or "Female",
  "date_of_death":    MM/DD/YYYY as written on the form,
  "ssn":              Full SSN with dashes (XXX-XX-XXXX) as written,
  "age":              Age as a string (digits only),
  "date_of_birth":    MM/DD/YYYY as written on the form,
  "birthplace":       City and state as written (e.g. "Phoenix, Ohio"),
  "residence_street": Street address as written,
  "county_residence": County name as written,
  "state_residence":  Two-letter US state abbreviation,
  "marital_status":   Exactly one of: "Married", "Divorced", "Widowed", "Never Married",
  "spouse_name":      Full name of spouse, or "" if blank/not applicable,
  "occupation":       Occupation as written,
  "industry":         Industry as written,
  "father_name":      Father's full name as written,
  "mother_name":      Mother's full name as written,
  "cause_a":          Immediate cause of death (Cause A / Line a),
  "cause_a_interval": Interval for Cause A (e.g. "4 months"),
  "cause_b":          Underlying cause (Cause B / Line b), or "" if blank,
  "cause_b_interval": Interval for Cause B, or "" if blank,
  "manner_of_death":  Exactly one of: "Natural", "Accident", "Suicide", "Homicide", "Pending",
  "place_of_death":   Facility or location name as written,
  "certifier_name":   Certifier's full name and title as written,
  "date_signed":      MM/DD/YYYY as written on the form
}

Rules:
- Transcribe values EXACTLY as they appear on the form, preserving spelling and punctuation.
- Use "" (empty string) for any field that is blank or unreadable.
- Dates must be in MM/DD/YYYY format as printed on the certificate.
- SSN must include dashes: XXX-XX-XXXX.
- Do NOT wrap the JSON in markdown code fences.
- Do NOT include any text before or after the JSON object.
- Output the raw JSON object only.
"""

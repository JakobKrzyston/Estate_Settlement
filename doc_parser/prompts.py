"""Prompt constants used by the extraction model; edit here to change model instructions."""

FIELDS = [
    "deceased_full_name", "date_of_birth", "date_of_death",
    "ssn_last4",
    "cause_of_death", "county", "state",
    "surviving_spouse", "filer_relationship",
]

EXTRACT_PROMPT = """You are extracting structured data from a death certificate.

Return ONLY a valid JSON object with exactly these keys:

  deceased_full_name  : Full legal name of the deceased (first, middle, last)
  date_of_birth       : Date of birth in YYYY-MM-DD format; use the format found if ISO is not determinable
  date_of_death       : Date of death in YYYY-MM-DD format
  ssn_last4           : LAST 4 DIGITS ONLY of the Social Security Number — never return more than 4 digits; if you can see more, truncate to the last 4
  cause_of_death      : Immediate cause of death as written (typically Part I, Line a on US certificates)
  county              : County of death or county of residence as listed
  state               : US state where the certificate was issued or recorded
  surviving_spouse    : Full name of the surviving spouse, or null if none listed
  filer_relationship  : Relationship of the informant or filer to the deceased (found near the informant/certifier section)
  confidence          : Float from 0.0 to 1.0 reflecting your overall extraction confidence across all fields

Rules:
- Use null (not an empty string) for any field you cannot locate or read.
- Lower the confidence score for each null or uncertain field.
- Do NOT wrap the JSON in markdown code fences.
- Do NOT include any text before or after the JSON object.
- Output the raw JSON object only.
"""

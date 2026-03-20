"""Prompt constants used by the extraction model; edit here to change model instructions."""

EXTRACT_PROMPT = """You are extracting structured data from a death certificate or related filing document.

Return ONLY a valid JSON object with this exact nested structure:

{
  "deceased": {
    "full_name":        Full legal name (first, middle, last),
    "date_of_birth":    YYYY-MM-DD,
    "date_of_death":    YYYY-MM-DD,
    "ssn_last4":        Last 4 digits of SSN only — never more than 4 digits,
    "cause_of_death":   Immediate cause as written (Part I, Line a on US certificates),
    "county":           County of death or residence,
    "state":            Two-letter US state abbreviation,
    "surviving_spouse": Full name of surviving spouse, or null if none listed
  },
  "filer": {
    "name":         Full name of the informant or applicant who filed this document,
    "relationship": Exactly one of: "surviving_spouse", "adult_child", "executor", "other"
                    Map using: Spouse / Wife / Husband           → "surviving_spouse"
                               Son / Daughter / Child            → "adult_child"
                               Personal Representative / Executor → "executor"
                               Parent / Sibling / Other           → "other"
    "address":      Mailing address of the filer as written, or null if not present
  },
  "confidence": Float from 0.0 to 1.0 reflecting overall extraction confidence across all fields
}

Rules:
- Use null (not an empty string) for any field you cannot locate or read.
- Lower the confidence score for each null or uncertain field.
- Do NOT wrap the JSON in markdown code fences.
- Do NOT include any text before or after the JSON object.
- Output the raw JSON object only.
"""

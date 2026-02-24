EXTRACTION_PROMPT = """You are an expert epidemiologist. Extract key epidemiologic data from the provided research study text.

CRITICAL: If the study reports MULTIPLE subgroups, stratified analyses, or meta-analyses, extract ONLY the PRIMARY/MAIN analysis result.
Use SINGLE VALUES, NOT LISTS.

ALWAYS return the COMPLETE JSON object below. Every key must be present.
Use null for missing numeric/object fields, empty string "" for missing string fields, and [] for missing arrays.
Do NOT omit any keys.

RETURN THIS EXACT SCHEMA:
{
  "metadata": {
    "study_id": "<string or null>",
    "title": "<FULL TITLE - REQUIRED, never null or empty>",
    "authors": "<string or null>",
    "year": <integer or null>,
    "journal": "<string or null>"
  },
  "methods": {
    "study_design": "<string or null>",
    "population": "<string or null>",
    "sample_size": <integer or null>,
    "exposure_definition": "<string or null>",
    "outcome_definition": "<string or null>"
  },
  "analysis": {
    "exposure": "<short string — empty string if study does not examine requested relationship>",
    "outcome": "<short string — empty string if study does not examine requested relationship>",
    "effect_measure": "<'OR'|'RR'|'HR'|'MD'|'SMD' or null>",
    "effect_value": <number or null>,
    "ci_lower": <number or null>,
    "ci_upper": <number or null>,
    "p_value": <number or null>,
    "group_statistics": {
      "exposed":   { "n": <integer or null>, "mean": <number or null>, "sd": <number or null> },
      "unexposed": { "n": <integer or null>, "mean": <number or null>, "sd": <number or null> }
    },
    "adjustment_variables": ["<string>", "..."]
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELD RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TITLE (metadata.title)
  • MANDATORY — never null, never empty string
  • Use the full title as written in the text

EXPOSURE / OUTCOME (analysis.exposure, analysis.outcome)
  • MANDATORY keys — always present in output
  • If the study DOES examine the requested relationship: short string description
  • If the study does NOT examine the requested relationship: empty string ""

EFFECT MEASURE (analysis.effect_measure)
  • Use ONLY: "OR", "RR", "HR", "MD", "SMD"
  • Normalize abbreviations: "MAOR", "meta-OR" → "OR"
  • Set to null if no effect size is reported

NUMERIC FIELDS (effect_value, ci_lower, ci_upper, p_value, sample_size)
  • Single numbers only — NEVER arrays or lists
  • Use the PRIMARY/MAIN result when multiple values are reported
  • Only populate ci_lower / ci_upper if a confidence interval is EXPLICITLY stated
  • Set to null if not reported

GROUP STATISTICS (analysis.group_statistics)
  • Always include the group_statistics object with both "exposed" and "unexposed" keys
  • Within each group, include only the fields (n, mean, sd) that are explicitly reported; set others to null
  • If no group statistics are reported at all, set both sub-objects to { "n": null, "mean": null, "sd": null }

ADJUSTMENT VARIABLES (analysis.adjustment_variables)
  • List of strings — empty array [] if none reported

ALL OTHER STRING FIELDS
  • null if not found in text

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Example A — Study WITH matching exposure/outcome and effect size:
{
  "metadata": { "study_id": null, "title": "Smoking and Lung Cancer Risk", "authors": "Smith J", "year": 2021, "journal": "Lancet" },
  "methods": { "study_design": "Case-control", "population": "Adults aged 40-70", "sample_size": 500, "exposure_definition": "Self-reported smoking >10 pack-years", "outcome_definition": "Histologically confirmed lung cancer" },
  "analysis": {
    "exposure": "cigarette smoking",
    "outcome": "lung cancer",
    "effect_measure": "OR",
    "effect_value": 4.5,
    "ci_lower": 3.2,
    "ci_upper": 6.3,
    "p_value": 0.001,
    "group_statistics": {
      "exposed":   { "n": 150, "mean": null, "sd": null },
      "unexposed": { "n": 350, "mean": null, "sd": null }
    },
    "adjustment_variables": ["age", "sex"]
  }
}

Example B — Study WITH matching exposure/outcome but NO effect size:
{
  "metadata": { "study_id": null, "title": "Smoking Review", "authors": null, "year": null, "journal": null },
  "methods": { "study_design": null, "population": null, "sample_size": null, "exposure_definition": null, "outcome_definition": null },
  "analysis": {
    "exposure": "smoking",
    "outcome": "lung cancer",
    "effect_measure": null,
    "effect_value": null,
    "ci_lower": null,
    "ci_upper": null,
    "p_value": null,
    "group_statistics": {
      "exposed":   { "n": null, "mean": null, "sd": null },
      "unexposed": { "n": null, "mean": null, "sd": null }
    },
    "adjustment_variables": []
  }
}

Example C — Study that does NOT examine the requested relationship:
{
  "metadata": { "study_id": null, "title": "Dietary Fiber and Colorectal Health", "authors": "A. Lee", "year": 2021, "journal": null },
  "methods": { "study_design": "Cohort", "population": null, "sample_size": null, "exposure_definition": null, "outcome_definition": null },
  "analysis": {
    "exposure": "",
    "outcome": "",
    "effect_measure": null,
    "effect_value": null,
    "ci_lower": null,
    "ci_upper": null,
    "p_value": null,
    "group_statistics": {
      "exposed":   { "n": null, "mean": null, "sd": null },
      "unexposed": { "n": null, "mean": null, "sd": null }
    },
    "adjustment_variables": []
  }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FINAL REMINDERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Extract ONLY the PRIMARY analysis result
• Only extract data EXPLICITLY stated in the text — do not infer or calculate
• Return ONLY valid JSON — no markdown, no code blocks, no commentary
• Every key in the schema must appear in your output

Study text:
{text}"""
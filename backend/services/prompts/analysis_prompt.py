"""Prompt for extracting study analysis / results (generic)."""

from backend.services.prompts.base_prompt import BASE_SYSTEM_MESSAGE, CRITICAL_RULES

ANALYSIS_EXTRACTION_PROMPT = """You are an expert epidemiologist extracting study analysis and results from a research paper.

Extract ONLY the following analysis fields. Do not extract metadata or methods data.

RETURN THIS EXACT SCHEMA:
{
  "analysis": {
    "exposure": "<short string — empty string if study does not examine requested relationship>",
    "outcome": "<short string — empty string if study does not examine requested relationship>",
    "effect_measure": "<'OR'|'RR'|'HR'|'MD'|'SMD'|'PROPORTION' or null>",
    "effect_value": <number or null — point estimate>,
    "ci_lower": <number or null — 95% CI lower bound>,
    "ci_upper": <number or null — 95% CI upper bound>,
    "p_value": <number or null — statistical p-value>,
    "group_statistics": {
      "exposed":   { "n": <integer or null>, "mean": <number or null>, "sd": <number or null> },
      "control":   { "n": <integer or null>, "mean": <number or null>, "sd": <number or null> }
    },
    "adjustment_variables": ["<string>", "..."]
  }
}

FIELD RULES:
• EXPOSURE / OUTCOME: MANDATORY keys — always present. If the study DOES examine the requested relationship: short string description. If NOT: empty string "".
• EFFECT_MEASURE: Use ONLY: "OR", "RR", "HR", "MD", "SMD", "PROPORTION". Normalize abbreviations (e.g., "MAOR" → "OR"). Set to null if not reported.
• EFFECT_VALUE: Single number only — NEVER arrays. Use the PRIMARY/MAIN result when multiple values are reported.
• CI_LOWER / CI_UPPER: Only populate if a confidence interval is EXPLICITLY stated. Set to null if not reported.
• P_VALUE: Statistical p-value if reported. Set to null if not reported.
• GROUP_STATISTICS: Always include the group_statistics object with both "exposed" and "control" keys. Set sub-fields to null if not reported.
• ADJUSTMENT_VARIABLES: List of strings — empty array [] if none reported.

""" + CRITICAL_RULES + """

EXAMPLE:
{
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
      "control":   { "n": 350, "mean": null, "sd": null }
    },
    "adjustment_variables": ["age", "sex"]
  }
}
"""

ANALYSIS_SYSTEM_MESSAGE = BASE_SYSTEM_MESSAGE + "\n" + """Focus exclusively on statistical results: effect measures, confidence intervals, p-values, and group-level statistics.
Do not extract bibliographic metadata or study design details."""

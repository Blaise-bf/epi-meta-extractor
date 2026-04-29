"""Prompt for extracting OR / RR data from epidemiological studies."""

from backend.services.prompts.base_prompt import BASE_SYSTEM_MESSAGE, CRITICAL_RULES

OR_RR_EXTRACTION_PROMPT = """You are an expert epidemiologist extracting odds ratio (OR) or risk ratio (RR) data from a research paper.

You must extract the effect measure (OR or RR), its point estimate, and 95% confidence interval.
If available, also extract the 2×2 contingency table (a, b, c, d cells) to enable recomputation.

RETURN THIS EXACT SCHEMA:
{
  "analysis": {
    "exposure": "<short string — empty string if not relevant>",
    "outcome": "<short string — empty string if not relevant>",
    "effect_measure": "<'OR'|'RR' or null>",
    "effect_value": <number or null — point estimate>,
    "ci_lower": <number or null — 95% CI lower bound>,
    "ci_upper": <number or null — 95% CI upper bound>,
    "p_value": <number or null — statistical p-value>,
    "two_by_two_table": {
      "a": <integer or null — Exposed with outcome>,
      "b": <integer or null — Exposed without outcome>,
      "c": <integer or null — Control with outcome>,
      "d": <integer or null — Control without outcome>
    },
    "group_statistics": {
      "exposed":   { "n": <integer or null>, "mean": <number or null>, "sd": <number or null> },
      "control":   { "n": <integer or null>, "mean": <number or null>, "sd": <number or null> }
    },
    "adjustment_variables": ["<string>", "..."]
  }
}

FIELD RULES:
• EFFECT_MEASURE: Must be "OR" or "RR". Normalize abbreviations (e.g., "MAOR" → "OR", "meta-RR" → "RR").
• EFFECT_VALUE: Point estimate (e.g., 2.5). Single number only.
• CI_LOWER / CI_UPPER: 95% confidence interval bounds. ci_lower ≤ ci_upper.
• P_VALUE: Statistical p-value if reported.
• TWO_BY_TWO_TABLE: Optional but highly valuable. Extract raw counts if reported:
    a = Exposed with outcome, b = Exposed without outcome,
    c = Control with outcome, d = Control without outcome.
  If the study does not report a 2×2 table, set all cells to null.
• GROUP_STATISTICS: Optional. Extract n, mean, sd for exposed and control groups if reported.
• ADJUSTMENT_VARIABLES: List of variables adjusted for in the analysis.

IMPORTANT:
• If the study reports an adjusted OR/RR (e.g., "adjusted OR = 2.1"), extract that as the primary effect_value.
• If both crude and adjusted are reported, prefer the adjusted value.
• If the study reports a 2×2 table, extract it even if the computed OR/RR is also reported.

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
    "two_by_two_table": {
      "a": 150,
      "b": 350,
      "c": 30,
      "d": 470
    },
    "group_statistics": {
      "exposed":   { "n": 500, "mean": null, "sd": null },
      "control":   { "n": 500, "mean": null, "sd": null }
    },
    "adjustment_variables": ["age", "sex", "bmi"]
  }
}
"""

OR_RR_SYSTEM_MESSAGE = BASE_SYSTEM_MESSAGE + "\n" + """You are extracting odds ratio (OR) or risk ratio (RR) data.
Focus on finding: (1) effect measure type, (2) point estimate + CI, (3) 2×2 contingency table if available."""

"""Prompt for extracting proportion data from epidemiological studies."""

from backend.services.prompts.base_prompt import BASE_SYSTEM_MESSAGE, CRITICAL_RULES

PROPORTION_EXTRACTION_PROMPT = """You are an expert epidemiologist extracting proportion data from a research paper.

A proportion is a single-group summary: e.g., prevalence, incidence proportion, or proportion with an outcome.
You must extract EITHER:
  (a) the number of events AND the total sample size, OR
  (b) the pre-computed proportion AND its standard error.

RETURN THIS EXACT SCHEMA:
{
  "analysis": {
    "exposure": "<short string — empty string if not relevant>",
    "outcome": "<short string — empty string if not relevant>",
    "effect_measure": "PROPORTION",
    "proportion_data": {
      "events": <integer or null — number of events (e.g., cases, deaths, successes)>,
      "sample_size": <integer or null — total sample size (denominator)>,
      "proportion": <number or null — pre-computed proportion between 0 and 1>,
      "se": <number or null — standard error of the proportion>,
      "ci_lower": <number or null — 95% CI lower bound>,
      "ci_upper": <number or null — 95% CI upper bound>
    },
    "adjustment_variables": ["<string>", "..."]
  }
}

FIELD RULES:
• EVENTS: Number of events (e.g., 150 cases out of 500). Must be ≥ 0.
• SAMPLE_SIZE: Total sample size (denominator). Must be ≥ 1.
• PROPORTION: Pre-computed proportion (events / sample_size). Must be between 0 and 1.
• SE: Standard error of the proportion. Must be ≥ 0.
• CI_LOWER / CI_UPPER: 95% confidence interval bounds. Must be between 0 and 1. ci_lower ≤ ci_upper.
• ADJUSTMENT_VARIABLES: List of variables adjusted for. Empty array [] if none.

IMPORTANT:
• If the study reports a proportion (e.g., "prevalence was 30%") but does NOT report events + sample_size, extract proportion and se (or CI) if available.
• If the study reports events + sample_size (e.g., "150 out of 500"), extract those and leave proportion / se as null.
• If neither is available, set all proportion_data fields to null.

""" + CRITICAL_RULES + """

EXAMPLE A — Events + sample size reported:
{
  "analysis": {
    "exposure": "gestational diabetes",
    "outcome": "macrosomia",
    "effect_measure": "PROPORTION",
    "proportion_data": {
      "events": 45,
      "sample_size": 300,
      "proportion": null,
      "se": null,
      "ci_lower": null,
      "ci_upper": null
    },
    "adjustment_variables": []
  }
}

EXAMPLE B — Proportion + CI reported:
{
  "analysis": {
    "exposure": "type 2 diabetes",
    "outcome": "diabetic retinopathy",
    "effect_measure": "PROPORTION",
    "proportion_data": {
      "events": null,
      "sample_size": null,
      "proportion": 0.32,
      "se": 0.03,
      "ci_lower": 0.26,
      "ci_upper": 0.38
    },
    "adjustment_variables": ["age", "duration_of_diabetes"]
  }
}
"""

PROPORTION_SYSTEM_MESSAGE = BASE_SYSTEM_MESSAGE + "\n" + """You are extracting proportion data (prevalence, incidence proportion, or single-group summary).
Focus on finding: (1) number of events and sample size, OR (2) pre-computed proportion with standard error or confidence interval."""

"""Prompt for extracting MD / SMD data from epidemiological studies."""

from backend.services.prompts.base_prompt import BASE_SYSTEM_MESSAGE, CRITICAL_RULES

MD_SMD_EXTRACTION_PROMPT = """You are an expert epidemiologist extracting mean difference (MD) or standardized mean difference (SMD) data from a research paper.

You must extract group-level continuous data (mean, sd, n) for both exposed and control groups.
If the study reports a pre-computed MD or SMD with CI, extract that as well.

RETURN THIS EXACT SCHEMA:
{
  "analysis": {
    "exposure": "<short string — empty string if not relevant>",
    "outcome": "<short string — empty string if not relevant>",
    "effect_measure": "<'MD'|'SMD' or null>",
    "effect_value": <number or null — point estimate>,
    "ci_lower": <number or null — 95% CI lower bound>,
    "ci_upper": <number or null — 95% CI upper bound>,
    "p_value": <number or null — statistical p-value>,
    "continuous_data": {
      "exposed_mean": <number or null>,
      "exposed_sd": <number or null — must be ≥ 0>,
      "exposed_n": <integer or null — must be ≥ 1>,
      "control_mean": <number or null>,
      "control_sd": <number or null — must be ≥ 0>,
      "control_n": <integer or null — must be ≥ 1>
    },
    "adjustment_variables": ["<string>", "..."]
  }
}

FIELD RULES:
• EFFECT_MEASURE: Must be "MD" or "SMD".
• EFFECT_VALUE: Pre-computed MD or SMD if reported. Single number only.
• CI_LOWER / CI_UPPER: 95% confidence interval bounds.
• CONTINUOUS_DATA: Group-level statistics. REQUIRED if effect_value is not reported.
  - exposed_mean / control_mean: Mean value for each group.
  - exposed_sd / control_sd: Standard deviation (must be ≥ 0).
  - exposed_n / control_n: Sample size (must be ≥ 1).
• ADJUSTMENT_VARIABLES: List of variables adjusted for.

IMPORTANT:
• If the study reports MD or SMD with CI, extract effect_value, ci_lower, ci_upper.
• If the study does NOT report MD/SMD but DOES report group means + SDs + Ns, extract continuous_data and leave effect_value as null.
• If the study reports multiple outcomes, extract data for the PRIMARY outcome only.

""" + CRITICAL_RULES + """

EXAMPLE A — Pre-computed MD + CI:
{
  "analysis": {
    "exposure": "high sodium diet",
    "outcome": "systolic blood pressure",
    "effect_measure": "MD",
    "effect_value": 5.2,
    "ci_lower": 2.1,
    "ci_upper": 8.3,
    "p_value": 0.001,
    "continuous_data": {
      "exposed_mean": 142.5,
      "exposed_sd": 12.3,
      "exposed_n": 150,
      "control_mean": 137.3,
      "control_sd": 11.8,
      "control_n": 150
    },
    "adjustment_variables": ["age", "sex", "bmi"]
  }
}

EXAMPLE B — Group means only (no pre-computed MD):
{
  "analysis": {
    "exposure": "exercise intervention",
    "outcome": "HbA1c",
    "effect_measure": "MD",
    "effect_value": null,
    "ci_lower": null,
    "ci_upper": null,
    "p_value": null,
    "continuous_data": {
      "exposed_mean": 7.2,
      "exposed_sd": 1.1,
      "exposed_n": 80,
      "control_mean": 8.1,
      "control_sd": 1.3,
      "control_n": 80
    },
    "adjustment_variables": []
  }
}
"""

MD_SMD_SYSTEM_MESSAGE = BASE_SYSTEM_MESSAGE + "\n" + """You are extracting mean difference (MD) or standardized mean difference (SMD) data.
Focus on finding: (1) pre-computed MD/SMD + CI if available, (2) group-level means, SDs, and sample sizes for both groups."""

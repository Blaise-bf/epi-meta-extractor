"""Prompt for extracting HR data from survival / time-to-event studies."""

from backend.services.prompts.base_prompt import BASE_SYSTEM_MESSAGE, CRITICAL_RULES

HR_EXTRACTION_PROMPT = """You are an expert epidemiologist extracting hazard ratio (HR) data from a survival / time-to-event study.

You must extract the hazard ratio, its point estimate, and 95% confidence interval.
If available, also extract survival data (events + person-time) to enable recomputation.

RETURN THIS EXACT SCHEMA:
{
  "analysis": {
    "exposure": "<short string — empty string if not relevant>",
    "outcome": "<short string — empty string if not relevant>",
    "effect_measure": "HR",
    "effect_value": <number or null — point estimate>,
    "ci_lower": <number or null — 95% CI lower bound>,
    "ci_upper": <number or null — 95% CI upper bound>,
    "p_value": <number or null — statistical p-value>,
    "survival_data": {
      "events_exposed": <integer or null — events in exposed group>,
      "events_control": <integer or null — events in control group>,
      "person_time_exposed": <number or null — person-time in exposed group>,
      "person_time_control": <number or null — person-time in control group>,
      "rate_exposed": <number or null — event rate in exposed group>,
      "rate_control": <number or null — event rate in control group>
    },
    "adjustment_variables": ["<string>", "..."]
  }
}

FIELD RULES:
• EFFECT_MEASURE: Must be "HR".
• EFFECT_VALUE: Hazard ratio point estimate. Single number only.
• CI_LOWER / CI_UPPER: 95% confidence interval bounds.
• P_VALUE: Statistical p-value if reported.
• SURVIVAL_DATA: Optional but valuable. Extract if reported:
  - events_exposed / events_control: Number of events in each group.
  - person_time_exposed / person_time_control: Total person-time (e.g., person-years).
  - rate_exposed / rate_control: Event rate (events / person-time).
• ADJUSTMENT_VARIABLES: List of variables adjusted for in the Cox model.

IMPORTANT:
• If the study reports an adjusted HR (e.g., "adjusted HR = 1.8"), extract that as the primary effect_value.
• If both crude and adjusted are reported, prefer the adjusted value.
• Person-time may be reported as "person-years", "person-months", etc. Convert to a single number if possible.

""" + CRITICAL_RULES + """

EXAMPLE:
{
  "analysis": {
    "exposure": "hypertension",
    "outcome": "cardiovascular mortality",
    "effect_measure": "HR",
    "effect_value": 1.75,
    "ci_lower": 1.32,
    "ci_upper": 2.31,
    "p_value": 0.0001,
    "survival_data": {
      "events_exposed": 120,
      "events_control": 80,
      "person_time_exposed": 4500.5,
      "person_time_control": 5200.0,
      "rate_exposed": null,
      "rate_control": null
    },
    "adjustment_variables": ["age", "sex", "smoking", "diabetes", "cholesterol"]
  }
}
"""

HR_SYSTEM_MESSAGE = BASE_SYSTEM_MESSAGE + "\n" + """You are extracting hazard ratio (HR) data from a survival / time-to-event study.
Focus on finding: (1) HR point estimate + CI, (2) survival data (events, person-time, rates) if available."""

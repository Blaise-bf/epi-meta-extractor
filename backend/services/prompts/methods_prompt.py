"""Prompt for extracting study methods."""

from backend.services.prompts.base_prompt import BASE_SYSTEM_MESSAGE

METHODS_EXTRACTION_PROMPT = """You are an expert epidemiologist extracting study methods from a research paper.

Extract ONLY the following methods fields. Do not extract metadata or results data.

RETURN THIS EXACT SCHEMA:
{
  "methods": {
    "study_design": "<string or null — e.g., Case-control, Cohort, RCT, Cross-sectional, Prospective cohort>",
    "population": "<string or null — description of the study population>",
    "sample_size": <integer or null — total sample size>,
    "exposure_definition": "<string or null — how exposure was defined/measured>",
    "outcome_definition": "<string or null — how outcome was defined/measured>"
  }
}

FIELD RULES:
• STUDY DESIGN: Common designs include "Case-control", "Cohort study", "Randomized controlled trial", "Cross-sectional", "Prospective cohort", "Retrospective cohort", "Nested case-control".
• POPULATION: Describe who was studied (e.g., "Adults aged 40-70 in urban China", "Pregnant women in tertiary hospitals").
• SAMPLE SIZE: Total number of participants. If multiple groups are reported, use the TOTAL across all groups.
• EXPOSURE DEFINITION: How was the exposure measured? (e.g., "Self-reported smoking status via questionnaire", "BMI ≥ 30 kg/m² from medical records").
• OUTCOME DEFINITION: How was the outcome measured? (e.g., "Histologically confirmed lung cancer", "HbA1c ≥ 6.5% from lab tests").

EXAMPLE:
{
  "methods": {
    "study_design": "Prospective cohort",
    "population": "Adults aged 40-70 in 12 cities across China",
    "sample_size": 12500,
    "exposure_definition": "Self-reported smoking status categorized as never, former, or current smoker",
    "outcome_definition": "Incident type 2 diabetes diagnosed via fasting glucose ≥ 7.0 mmol/L or HbA1c ≥ 6.5%"
  }
}
"""

METHODS_SYSTEM_MESSAGE = BASE_SYSTEM_MESSAGE + "\n" + """Focus exclusively on study design, population, sample size, and how exposure and outcome were defined.
Do not extract bibliographic metadata or statistical results."""

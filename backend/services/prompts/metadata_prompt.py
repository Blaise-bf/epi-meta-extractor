"""Prompt for extracting study metadata."""

from backend.services.prompts.base_prompt import BASE_SYSTEM_MESSAGE

METADATA_EXTRACTION_PROMPT = """You are an expert epidemiologist extracting study metadata from a research paper.

Extract ONLY the following metadata fields. Do not extract methods or results data.

RETURN THIS EXACT SCHEMA:
{
  "metadata": {
    "study_id": "<string or null — DOI, PMID, or other identifier>",
    "title": "<FULL TITLE — REQUIRED, never null or empty>",
    "authors": "<First author or all authors — string or null>",
    "year": <integer or null — publication year>,
    "journal": "<string or null>",
    "country": "<Country where the study was conducted — string or null>",
    "continent": "<Continent inferred from country — string or null>"
  }
}

FIELD RULES:
• TITLE (metadata.title): MANDATORY — never null, never empty string. Use the full title as written.
• AUTHORS: Extract ONLY the first author (e.g., "Smith J"). Do NOT include multiple authors, "et al.", or commas.
• YEAR: Extract the publication year. Must be a 4-digit integer between 1900 and 2100.
• COUNTRY: Extract the country where the study was conducted (e.g., from the methods section or author affiliations).
• CONTINENT: Optional. Infer from the country if possible (e.g., "United States" → "North America", "Nigeria" → "Africa").

EXAMPLE:
{
  "metadata": {
    "study_id": "10.1000/j.example.2024.01",
    "title": "Smoking and Lung Cancer Risk: A Global Cohort Study",
    "authors": "Smith J",
    "year": 2024,
    "journal": "Lancet Oncology",
    "country": "United Kingdom",
    "continent": "Europe"
  }
}
"""

METADATA_SYSTEM_MESSAGE = BASE_SYSTEM_MESSAGE + "\n" + """Focus exclusively on bibliographic metadata: title, authors, year, journal, identifiers, and geographic location.
Do not extract methods, results, or statistical data."""

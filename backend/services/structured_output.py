"""LangChain structured output schemas for effect-size-specific extraction.

Each effect measure has its own Pydantic schema that LangChain's
`with_structured_output()` uses to constrain the LLM response.
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class GroupStatistics(BaseModel):
    """Group-level statistics (mean, sd, n)."""
    n: Optional[int] = Field(None, description="Group size / sample size")
    mean: Optional[float] = Field(None, description="Mean value")
    sd: Optional[float] = Field(None, description="Standard deviation")


class GroupData(BaseModel):
    """Exposed vs control group statistics."""
    exposed: Optional[GroupStatistics] = Field(None, description="Exposed / treatment group")
    control: Optional[GroupStatistics] = Field(None, description="Control / unexposed group")


# ---------------------------------------------------------------------------
# Metadata & Methods
# ---------------------------------------------------------------------------

class MetadataOutput(BaseModel):
    """Study metadata extracted from the document."""
    study_id: Optional[str] = Field(None, description="Study identifier (DOI, PMID, etc.)")
    title: Optional[str] = Field(None, description="Study title")
    authors: Optional[str] = Field(None, description="Comma-separated author names")
    year: Optional[int] = Field(None, description="Publication year")
    journal: Optional[str] = Field(None, description="Journal name")


class MethodsOutput(BaseModel):
    """Study methods extracted from the document."""
    study_design: Optional[str] = Field(None, description="Study design (e.g., Case-control, Cohort, RCT)")
    population: Optional[str] = Field(None, description="Study population description")
    sample_size: Optional[int] = Field(None, description="Total sample size")
    exposure_definition: Optional[str] = Field(None, description="How exposure was defined/measured")
    outcome_definition: Optional[str] = Field(None, description="How outcome was defined/measured")


# ---------------------------------------------------------------------------
# Effect-size-specific analysis outputs
# ---------------------------------------------------------------------------

class TwoByTwoTable(BaseModel):
    """Contingency table for binary outcomes (OR / RR)."""
    a: Optional[int] = Field(None, description="Exposed with outcome")
    b: Optional[int] = Field(None, description="Exposed without outcome")
    c: Optional[int] = Field(None, description="Control with outcome")
    d: Optional[int] = Field(None, description="Control without outcome")


class ORRRAnalysisOutput(BaseModel):
    """Analysis block for odds ratio or risk ratio."""
    exposure: Optional[str] = Field(None, description="Exposure / risk factor")
    outcome: Optional[str] = Field(None, description="Outcome / disease")
    effect_measure: Optional[str] = Field(None, description="OR or RR")
    effect_value: Optional[float] = Field(None, description="Point estimate")
    ci_lower: Optional[float] = Field(None, description="95% CI lower bound")
    ci_upper: Optional[float] = Field(None, description="95% CI upper bound")
    p_value: Optional[float] = Field(None, description="Statistical p-value")
    two_by_two_table: Optional[TwoByTwoTable] = Field(None, description="2×2 contingency table")
    group_statistics: Optional[GroupData] = Field(None, description="Group-level statistics")
    adjustment_variables: Optional[List[str]] = Field(default_factory=list)


class SurvivalData(BaseModel):
    """Survival / time-to-event data for hazard ratio."""
    events_exposed: Optional[int] = Field(None, description="Events in exposed group")
    events_control: Optional[int] = Field(None, description="Events in control group")
    person_time_exposed: Optional[float] = Field(None, description="Person-time in exposed group")
    person_time_control: Optional[float] = Field(None, description="Person-time in control group")
    rate_exposed: Optional[float] = Field(None, description="Event rate in exposed group")
    rate_control: Optional[float] = Field(None, description="Event rate in control group")


class HRAnalysisOutput(BaseModel):
    """Analysis block for hazard ratio."""
    exposure: Optional[str] = Field(None, description="Exposure / risk factor")
    outcome: Optional[str] = Field(None, description="Outcome / disease")
    effect_measure: Optional[str] = Field("HR", description="Hazard Ratio")
    effect_value: Optional[float] = Field(None, description="Point estimate")
    ci_lower: Optional[float] = Field(None, description="95% CI lower bound")
    ci_upper: Optional[float] = Field(None, description="95% CI upper bound")
    p_value: Optional[float] = Field(None, description="Statistical p-value")
    survival_data: Optional[SurvivalData] = Field(None, description="Survival / time-to-event data")
    adjustment_variables: Optional[List[str]] = Field(default_factory=list)


class ContinuousData(BaseModel):
    """Continuous outcome data for mean difference or standardized mean difference."""
    exposed_mean: Optional[float] = Field(None, description="Mean in exposed group")
    exposed_sd: Optional[float] = Field(None, description="SD in exposed group")
    exposed_n: Optional[int] = Field(None, description="N in exposed group")
    control_mean: Optional[float] = Field(None, description="Mean in control group")
    control_sd: Optional[float] = Field(None, description="SD in control group")
    control_n: Optional[int] = Field(None, description="N in control group")


class MDSMDAnalysisOutput(BaseModel):
    """Analysis block for mean difference or standardized mean difference."""
    exposure: Optional[str] = Field(None, description="Exposure / risk factor")
    outcome: Optional[str] = Field(None, description="Outcome / disease")
    effect_measure: Optional[str] = Field(None, description="MD or SMD")
    effect_value: Optional[float] = Field(None, description="Point estimate")
    ci_lower: Optional[float] = Field(None, description="95% CI lower bound")
    ci_upper: Optional[float] = Field(None, description="95% CI upper bound")
    p_value: Optional[float] = Field(None, description="Statistical p-value")
    continuous_data: Optional[ContinuousData] = Field(None, description="Group-level continuous data")
    adjustment_variables: Optional[List[str]] = Field(default_factory=list)


class ProportionDataOutput(BaseModel):
    """Data for a single proportion (e.g., prevalence, incidence)."""
    events: Optional[int] = Field(None, description="Number of events")
    sample_size: Optional[int] = Field(None, description="Total sample size (denominator)")
    proportion: Optional[float] = Field(None, description="Pre-computed proportion (0–1)")
    se: Optional[float] = Field(None, description="Standard error of the proportion")
    ci_lower: Optional[float] = Field(None, description="95% CI lower bound")
    ci_upper: Optional[float] = Field(None, description="95% CI upper bound")


class ProportionAnalysisOutput(BaseModel):
    """Analysis block for proportion effect measure."""
    exposure: Optional[str] = Field(None, description="Exposure / risk factor")
    outcome: Optional[str] = Field(None, description="Outcome / disease")
    effect_measure: Optional[str] = Field("PROPORTION", description="Effect measure type")
    proportion_data: Optional[ProportionDataOutput] = Field(None, description="Proportion-specific data")
    adjustment_variables: Optional[List[str]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Top-level structured outputs
# ---------------------------------------------------------------------------

class ExtractedStudyStructuredOutput(BaseModel):
    """Complete structured output for study extraction.

    Used as the schema for LangChain's `with_structured_output()`.
    """
    metadata: Optional[MetadataOutput] = Field(None, description="Study metadata")
    methods: Optional[MethodsOutput] = Field(None, description="Study methods")
    analysis: Optional[BaseModel] = Field(None, description="Study analysis (effect-size-specific)")


# Mapping of effect measures to their structured output schemas
EFFECT_SCHEMA_MAP = {
    "OR": ORRRAnalysisOutput,
    "RR": ORRRAnalysisOutput,
    "HR": HRAnalysisOutput,
    "MD": MDSMDAnalysisOutput,
    "SMD": MDSMDAnalysisOutput,
    "PROPORTION": ProportionAnalysisOutput,
}


def get_effect_schema(effect_type: str):
    """Get the Pydantic schema for a given effect measure.

    Args:
        effect_type: One of PROPORTION, OR, RR, MD, SMD, HR

    Returns:
        Pydantic BaseModel class for the effect measure.
        Falls back to ORRRAnalysisOutput if not recognized.
    """
    return EFFECT_SCHEMA_MAP.get(effect_type.upper(), ORRRAnalysisOutput)

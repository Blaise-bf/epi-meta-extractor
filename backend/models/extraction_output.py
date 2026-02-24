"""Pydantic models for LLM extraction with LangChain structured output"""

from pydantic import BaseModel, Field
from typing import Optional, List

class GroupStatistics(BaseModel):
    """Group statistics for exposed/control groups"""
    mean: Optional[float] = Field(None, description="Mean value")
    sd: Optional[float] = Field(None, description="Standard deviation")
    n: Optional[int] = Field(None, description="Group size/sample size")


class Metadata(BaseModel):
    """Study metadata - only includes fields found in the document"""
    study_id: Optional[str] = Field(None, description="Study identifier from document")
    title: Optional[str] = Field(None, description="Study title")
    authors: Optional[str] = Field(None, description="Comma-separated author names")
    year: Optional[int] = Field(None, description="Publication year")
    journal: Optional[str] = Field(None, description="Journal name")

    class Config:
        # Exclude None values when serializing
        exclude_none = True


class Methods(BaseModel):
    """Study methods - only includes fields found in the document"""
    study_design: Optional[str] = Field(
        None,
        description="Study design (e.g., Case-control, Cohort study, RCT, Cross-sectional, Prospective cohort)"
    )
    population: Optional[str] = Field(None, description="Study population description")
    sample_size: Optional[int] = Field(None, description="Total sample size")
    exposure_definition: Optional[str] = Field(None, description="How exposure was defined/measured")
    outcome_definition: Optional[str] = Field(None, description="How outcome was defined/measured")

    class Config:
        exclude_none = True


class Analysis(BaseModel):
    """Study analysis results - only includes fields found in the document"""
    exposure: Optional[str] = Field(None, description="Exposure/risk factor description")
    outcome: Optional[str] = Field(None, description="Outcome/disease description")
    effect_measure: Optional[str] = Field(
        None,
        description="Type of effect measure (OR, RR, HR, MD, SMD)"
    )
    effect_value: Optional[float] = Field(None, description="Point estimate of effect measure")
    ci_lower: Optional[float] = Field(None, description="95% confidence interval lower bound")
    ci_upper: Optional[float] = Field(None, description="95% confidence interval upper bound")
    p_value: Optional[float] = Field(None, description="Statistical p-value if reported")
    group_statistics: Optional[dict] = Field(
        None,
        description="Group statistics for exposed/unexposed or treatment/control groups"
    )
    adjustment_variables: Optional[List[str]] = Field(
        None,
        description="Variables that were adjusted for in the analysis"
    )

    class Config:
        exclude_none = True


class ExtractedStudyData(BaseModel):
    """Complete extracted study data with structured output"""
    metadata: Optional[Metadata] = Field(None, description="Study metadata")
    methods: Optional[Methods] = Field(None, description="Study methods")
    analysis: Optional[Analysis] = Field(None, description="Study analysis and results")
    effect_measure_type: Optional[str] = Field(None, description="Effect measure type from the study")

    class Config:
        exclude_none = True

    def dict(self, **kwargs):
        """Override dict to exclude None values"""
        kwargs['exclude_none'] = True
        return super().dict(**kwargs)

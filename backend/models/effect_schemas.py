"""Effect-size-specific Pydantic models for structured extraction.

Each effect measure has its own schema that defines exactly what data
should be extracted from epidemiological studies.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from enum import Enum
import math


class EffectMeasure(str, Enum):
    """Supported effect measures for meta-analysis."""
    OR = "OR"
    RR = "RR"
    HR = "HR"
    MD = "MD"
    SMD = "SMD"
    PROPORTION = "PROPORTION"


# ---------------------------------------------------------------------------
# Shared / base models
# ---------------------------------------------------------------------------

class GroupStatistics(BaseModel):
    """Group-level statistics (mean, sd, n)."""
    mean: Optional[float] = Field(None, description="Mean value")
    sd: Optional[float] = Field(None, description="Standard deviation")
    n: Optional[int] = Field(None, description="Group size / sample size")


class GroupData(BaseModel):
    """Exposed vs control group statistics."""
    exposed: Optional[GroupStatistics] = Field(None, description="Exposed / treatment group")
    control: Optional[GroupStatistics] = Field(None, description="Control / unexposed group")


# ---------------------------------------------------------------------------
# Proportion
# ---------------------------------------------------------------------------

class ProportionData(BaseModel):
    """Data for a single proportion (e.g., prevalence, incidence).

    Either (events + sample_size) OR (proportion + se) must be provided.
    If events + sample_size are given, proportion and se can be computed.
    """
    events: Optional[int] = Field(
        None,
        ge=0,
        description="Number of events (e.g., cases, deaths, successes)"
    )
    sample_size: Optional[int] = Field(
        None,
        ge=1,
        description="Total sample size (denominator)"
    )
    proportion: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Pre-computed proportion (events / sample_size)"
    )
    se: Optional[float] = Field(
        None,
        ge=0.0,
        description="Standard error of the proportion"
    )
    ci_lower: Optional[float] = Field(None, ge=0.0, le=1.0)
    ci_upper: Optional[float] = Field(None, ge=0.0, le=1.0)

    @field_validator("ci_upper")
    @classmethod
    def _ci_order(cls, v, info):
        lower = info.data.get("ci_lower")
        if lower is not None and v is not None and v < lower:
            raise ValueError("ci_upper must be >= ci_lower")
        return v

    def compute_proportion(self) -> Optional[float]:
        """Compute proportion from events / sample_size if not provided."""
        if self.proportion is not None:
            return self.proportion
        if self.events is not None and self.sample_size is not None and self.sample_size > 0:
            return self.events / self.sample_size
        return None

    def compute_se(self) -> Optional[float]:
        """Compute standard error from proportion and sample size."""
        if self.se is not None:
            return self.se
        p = self.compute_proportion()
        if p is not None and self.sample_size is not None and self.sample_size > 0:
            return math.sqrt(p * (1 - p) / self.sample_size)
        return None


# ---------------------------------------------------------------------------
# Two-by-two table (for OR / RR)
# ---------------------------------------------------------------------------

class TwoByTwoTable(BaseModel):
    """Contingency table for binary outcomes.

    Layout:
                Outcome+   Outcome-
        Exposed     a          b
        Control     c          d
    """
    a: Optional[int] = Field(None, ge=0, description="Exposed with outcome")
    b: Optional[int] = Field(None, ge=0, description="Exposed without outcome")
    c: Optional[int] = Field(None, ge=0, description="Control with outcome")
    d: Optional[int] = Field(None, ge=0, description="Control without outcome")

    def compute_or(self) -> Optional[float]:
        """Compute odds ratio from 2×2 table."""
        if all(v is not None and v >= 0 for v in (self.a, self.b, self.c, self.d)):
            # Add 0.5 continuity correction if any cell is zero
            a, b, c, d = self.a, self.b, self.c, self.d
            if a == 0 or b == 0 or c == 0 or d == 0:
                a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5
            return (a * d) / (b * c)
        return None

    def compute_rr(self) -> Optional[float]:
        """Compute risk ratio from 2×2 table."""
        if all(v is not None and v >= 0 for v in (self.a, self.b, self.c, self.d)):
            a, b, c, d = self.a, self.b, self.c, self.d
            if a + b == 0 or c + d == 0:
                return None
            return (a / (a + b)) / (c / (c + d))
        return None

    def is_complete(self) -> bool:
        return all(v is not None for v in (self.a, self.b, self.c, self.d))


# ---------------------------------------------------------------------------
# Continuous data (for MD / SMD)
# ---------------------------------------------------------------------------

class ContinuousData(BaseModel):
    """Continuous outcome data for mean difference or standardized mean difference.

    Requires group statistics (mean, sd, n) for both exposed and control groups.
    """
    exposed_mean: Optional[float] = Field(None, description="Mean in exposed group")
    exposed_sd: Optional[float] = Field(None, ge=0, description="SD in exposed group")
    exposed_n: Optional[int] = Field(None, ge=1, description="N in exposed group")
    control_mean: Optional[float] = Field(None, description="Mean in control group")
    control_sd: Optional[float] = Field(None, ge=0, description="SD in control group")
    control_n: Optional[int] = Field(None, ge=1, description="N in control group")

    def compute_md(self) -> Optional[float]:
        """Compute mean difference = exposed_mean - control_mean."""
        if self.exposed_mean is not None and self.control_mean is not None:
            return self.exposed_mean - self.control_mean
        return None

    def compute_smd(self) -> Optional[float]:
        """Compute standardized mean difference (Cohen's d)."""
        md = self.compute_md()
        if md is None:
            return None
        if self.exposed_sd is not None and self.control_sd is not None:
            # Pooled standard deviation
            n1 = self.exposed_n or 1
            n2 = self.control_n or 1
            pooled_sd = math.sqrt(
                ((n1 - 1) * self.exposed_sd ** 2 + (n2 - 1) * self.control_sd ** 2)
                / (n1 + n2 - 2)
            )
            if pooled_sd > 0:
                return md / pooled_sd
        return None

    def is_complete(self) -> bool:
        return all(
            v is not None
            for v in (
                self.exposed_mean,
                self.exposed_sd,
                self.exposed_n,
                self.control_mean,
                self.control_sd,
                self.control_n,
            )
        )


# ---------------------------------------------------------------------------
# Survival data (for HR)
# ---------------------------------------------------------------------------

class SurvivalData(BaseModel):
    """Survival / time-to-event data for hazard ratio.

    Either (effect_value + CI) OR (events + person_time) must be provided.
    """
    events_exposed: Optional[int] = Field(None, ge=0, description="Events in exposed group")
    events_control: Optional[int] = Field(None, ge=0, description="Events in control group")
    person_time_exposed: Optional[float] = Field(
        None, ge=0, description="Person-time in exposed group (e.g., person-years)"
    )
    person_time_control: Optional[float] = Field(
        None, ge=0, description="Person-time in control group"
    )
    rate_exposed: Optional[float] = Field(
        None, ge=0, description="Event rate in exposed group (events / person_time)"
    )
    rate_control: Optional[float] = Field(
        None, ge=0, description="Event rate in control group"
    )

    def compute_hr_from_rates(self) -> Optional[float]:
        """Compute HR from event rates if available."""
        if (
            self.rate_exposed is not None
            and self.rate_control is not None
            and self.rate_control > 0
        ):
            return self.rate_exposed / self.rate_control
        if (
            self.events_exposed is not None
            and self.person_time_exposed is not None
            and self.person_time_exposed > 0
            and self.events_control is not None
            and self.person_time_control is not None
            and self.person_time_control > 0
        ):
            return (self.events_exposed / self.person_time_exposed) / (
                self.events_control / self.person_time_control
            )
        return None

    def is_complete(self) -> bool:
        return all(
            v is not None
            for v in (
                self.events_exposed,
                self.events_control,
                self.person_time_exposed,
                self.person_time_control,
            )
        )


# ---------------------------------------------------------------------------
# Effect-size-specific analysis models
# ---------------------------------------------------------------------------

class ProportionAnalysis(BaseModel):
    """Analysis block for proportion effect measure."""
    exposure: Optional[str] = Field(None, description="Exposure / risk factor")
    outcome: Optional[str] = Field(None, description="Outcome / disease")
    effect_measure: Optional[str] = Field("PROPORTION", description="Effect measure type")
    proportion_data: Optional[ProportionData] = Field(None, description="Proportion-specific data")
    adjustment_variables: Optional[List[str]] = Field(default_factory=list)


class ORRRAnalysis(BaseModel):
    """Analysis block for odds ratio or risk ratio."""
    exposure: Optional[str] = Field(None, description="Exposure / risk factor")
    outcome: Optional[str] = Field(None, description="Outcome / disease")
    effect_measure: Optional[str] = Field(None, description="OR or RR")
    effect_value: Optional[float] = Field(None, description="Point estimate")
    ci_lower: Optional[float] = Field(None, description="95% CI lower bound")
    ci_upper: Optional[float] = Field(None, description="95% CI upper bound")
    p_value: Optional[float] = Field(None, description="Statistical p-value")
    two_by_two_table: Optional[TwoByTwoTable] = Field(None, description="2×2 contingency table")
    adjustment_variables: Optional[List[str]] = Field(default_factory=list)


class MDSMDAnalysis(BaseModel):
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


class HRAnalysis(BaseModel):
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


# ---------------------------------------------------------------------------
# Unified analysis model (used in the main extraction output)
# ---------------------------------------------------------------------------

class Analysis(BaseModel):
    """Unified analysis model that can hold any effect-size-specific data.

    The `effect_measure_type` field determines which sub-model is populated.
    """
    exposure: Optional[str] = None
    outcome: Optional[str] = None
    effect_measure: Optional[EffectMeasure] = None
    effect_value: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    p_value: Optional[float] = None
    group_statistics: Optional[GroupData] = None

    # Effect-size-specific blocks (only one should be populated per extraction)
    proportion_data: Optional[ProportionData] = None
    two_by_two_table: Optional[TwoByTwoTable] = None
    continuous_data: Optional[ContinuousData] = None
    survival_data: Optional[SurvivalData] = None

    adjustment_variables: Optional[List[str]] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "exposure": "cigarette smoking",
                "outcome": "lung cancer",
                "effect_measure": "OR",
                "effect_value": 4.5,
                "ci_lower": 3.2,
                "ci_upper": 6.3,
                "p_value": 0.001,
                "two_by_two_table": {"a": 150, "b": 350, "c": 30, "d": 470},
                "adjustment_variables": ["age", "sex"],
            }
        }

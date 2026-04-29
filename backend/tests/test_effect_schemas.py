"""Tests for effect-size-specific Pydantic models."""

import pytest
import math
from backend.models.effect_schemas import (
    EffectMeasure,
    ProportionData,
    TwoByTwoTable,
    ContinuousData,
    SurvivalData,
    GroupStatistics,
    GroupData,
    Analysis,
)


class TestEffectMeasure:
    """Test the EffectMeasure enum."""

    def test_all_measures_present(self):
        measures = [e.value for e in EffectMeasure]
        assert sorted(measures) == sorted(["OR", "RR", "HR", "MD", "SMD", "PROPORTION"])

    def test_proportion_member(self):
        assert EffectMeasure.PROPORTION == "PROPORTION"


class TestProportionData:
    """Test ProportionData model and computations."""

    def test_basic_creation(self):
        pd = ProportionData(events=45, sample_size=300)
        assert pd.events == 45
        assert pd.sample_size == 300

    def test_compute_proportion_from_events(self):
        pd = ProportionData(events=45, sample_size=300)
        assert pd.compute_proportion() == 0.15

    def test_compute_proportion_when_already_set(self):
        pd = ProportionData(proportion=0.25, sample_size=100)
        assert pd.compute_proportion() == 0.25

    def test_compute_se(self):
        pd = ProportionData(events=45, sample_size=300)
        expected_se = math.sqrt(0.15 * 0.85 / 300)
        assert pd.compute_se() == pytest.approx(expected_se)

    def test_ci_validation_order(self):
        with pytest.raises(ValueError, match="ci_upper must be >= ci_lower"):
            ProportionData(proportion=0.5, ci_lower=0.6, ci_upper=0.4)

    def test_proportion_bounds_validation(self):
        with pytest.raises(ValueError):
            ProportionData(proportion=1.5)


class TestTwoByTwoTable:
    """Test TwoByTwoTable model and computations."""

    def test_basic_creation(self):
        t2 = TwoByTwoTable(a=150, b=350, c=30, d=470)
        assert t2.a == 150
        assert t2.is_complete()

    def test_compute_or(self):
        t2 = TwoByTwoTable(a=150, b=350, c=30, d=470)
        expected_or = (150 * 470) / (350 * 30)
        assert t2.compute_or() == pytest.approx(expected_or)

    def test_compute_or_with_continuity_correction(self):
        t2 = TwoByTwoTable(a=10, b=0, c=5, d=100)
        # With 0.5 continuity correction: a=10.5, b=0.5, c=5.5, d=100.5
        expected = (10.5 * 100.5) / (0.5 * 5.5)
        assert t2.compute_or() == pytest.approx(expected)

    def test_compute_rr(self):
        t2 = TwoByTwoTable(a=150, b=350, c=30, d=470)
        expected_rr = (150 / 500) / (30 / 500)
        assert t2.compute_rr() == pytest.approx(expected_rr)

    def test_incomplete_table(self):
        t2 = TwoByTwoTable(a=150, b=350)
        assert not t2.is_complete()
        assert t2.compute_or() is None


class TestContinuousData:
    """Test ContinuousData model and computations."""

    def test_basic_creation(self):
        cd = ContinuousData(
            exposed_mean=142.5, exposed_sd=12.3, exposed_n=150,
            control_mean=137.3, control_sd=11.8, control_n=150
        )
        assert cd.exposed_mean == 142.5
        assert cd.is_complete()

    def test_compute_md(self):
        cd = ContinuousData(
            exposed_mean=142.5, exposed_sd=12.3, exposed_n=150,
            control_mean=137.3, control_sd=11.8, control_n=150
        )
        assert cd.compute_md() == pytest.approx(5.2)

    def test_compute_smd(self):
        cd = ContinuousData(
            exposed_mean=142.5, exposed_sd=12.3, exposed_n=150,
            control_mean=137.3, control_sd=11.8, control_n=150
        )
        smd = cd.compute_smd()
        assert smd is not None
        assert smd > 0

    def test_incomplete_data(self):
        cd = ContinuousData(exposed_mean=100, exposed_n=50)
        assert not cd.is_complete()
        assert cd.compute_md() is None


class TestSurvivalData:
    """Test SurvivalData model and computations."""

    def test_basic_creation(self):
        sd = SurvivalData(
            events_exposed=120, events_control=80,
            person_time_exposed=4500.5, person_time_control=5200.0
        )
        assert sd.events_exposed == 120
        assert sd.is_complete()

    def test_compute_hr_from_rates(self):
        sd = SurvivalData(
            events_exposed=120, events_control=80,
            person_time_exposed=4500.5, person_time_control=5200.0
        )
        hr = sd.compute_hr_from_rates()
        expected = (120 / 4500.5) / (80 / 5200.0)
        assert hr == pytest.approx(expected)

    def test_compute_hr_from_precomputed_rates(self):
        sd = SurvivalData(rate_exposed=0.0267, rate_control=0.0154)
        hr = sd.compute_hr_from_rates()
        assert hr == pytest.approx(0.0267 / 0.0154)

    def test_incomplete_data(self):
        sd = SurvivalData(events_exposed=120)
        assert not sd.is_complete()
        assert sd.compute_hr_from_rates() is None


class TestGroupStatistics:
    """Test GroupStatistics and GroupData models."""

    def test_group_statistics_creation(self):
        gs = GroupStatistics(mean=10.5, sd=2.3, n=100)
        assert gs.mean == 10.5
        assert gs.sd == 2.3
        assert gs.n == 100

    def test_group_data_creation(self):
        gd = GroupData(
            exposed=GroupStatistics(mean=12.0, sd=2.0, n=50),
            control=GroupStatistics(mean=10.0, sd=2.5, n=50)
        )
        assert gd.exposed.mean == 12.0
        assert gd.control.mean == 10.0

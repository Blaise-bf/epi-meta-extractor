"""Tests for effect-size-specific extraction agents."""

import pytest
import math
from backend.services.agents.proportion_agent import ProportionAgent
from backend.services.agents.or_rr_agent import ORRRAgent
from backend.services.agents.md_smd_agent import MDSMDAgent
from backend.services.agents.hr_agent import HRAgent
from backend.services.agents import get_agent, process_with_agent


class TestProportionAgent:
    """Test ProportionAgent validation and computation."""

    def setup_method(self):
        self.agent = ProportionAgent()

    def test_validate_complete_primary_data(self):
        data = {
            "analysis": {
                "proportion_data": {
                    "events": 45,
                    "sample_size": 300,
                }
            }
        }
        errors = self.agent.validate(data)
        assert len(errors) == 0

    def test_validate_complete_alternative_data(self):
        data = {
            "analysis": {
                "proportion_data": {
                    "proportion": 0.25,
                    "se": 0.03,
                }
            }
        }
        errors = self.agent.validate(data)
        assert len(errors) == 0

    def test_validate_incomplete_data(self):
        data = {
            "analysis": {
                "proportion_data": {
                    "events": 45,
                }
            }
        }
        errors = self.agent.validate(data)
        assert len(errors) > 0
        assert any("incomplete" in e.lower() for e in errors)

    def test_validate_negative_events(self):
        data = {
            "analysis": {
                "proportion_data": {
                    "events": -5,
                    "sample_size": 300,
                }
            }
        }
        errors = self.agent.validate(data)
        assert any("events" in e.lower() for e in errors)

    def test_compute_proportion(self):
        data = {
            "analysis": {
                "proportion_data": {
                    "events": 45,
                    "sample_size": 300,
                }
            }
        }
        result = self.agent.compute_effect_size(data)
        pd = result["analysis"]["proportion_data"]
        assert pd["proportion"] == 0.15
        assert "se" in pd
        assert pd["se"] > 0

    def test_compute_ci(self):
        data = {
            "analysis": {
                "proportion_data": {
                    "events": 45,
                    "sample_size": 300,
                }
            }
        }
        result = self.agent.compute_effect_size(data)
        pd = result["analysis"]["proportion_data"]
        assert "ci_lower" in pd
        assert "ci_upper" in pd
        assert pd["ci_lower"] < pd["ci_upper"]
        assert 0 <= pd["ci_lower"] <= 1
        assert 0 <= pd["ci_upper"] <= 1

    def test_should_retry_when_incomplete(self):
        data = {
            "analysis": {
                "proportion_data": {
                    "events": 45,
                }
            }
        }
        assert self.agent.should_retry(data)

    def test_should_not_retry_when_complete(self):
        data = {
            "analysis": {
                "proportion_data": {
                    "events": 45,
                    "sample_size": 300,
                }
            }
        }
        assert not self.agent.should_retry(data)


class TestORRRAgent:
    """Test ORRRAgent validation and computation."""

    def setup_method(self):
        self.agent = ORRRAgent()

    def test_validate_complete_effect_value(self):
        data = {
            "analysis": {
                "effect_measure": "OR",
                "effect_value": 2.5,
                "ci_lower": 1.8,
                "ci_upper": 3.2,
            }
        }
        errors = self.agent.validate(data)
        assert len(errors) == 0

    def test_validate_complete_two_by_two(self):
        data = {
            "analysis": {
                "effect_measure": "OR",
                "two_by_two_table": {
                    "a": 150, "b": 350, "c": 30, "d": 470
                }
            }
        }
        errors = self.agent.validate(data)
        assert len(errors) == 0

    def test_validate_incomplete(self):
        data = {
            "analysis": {
                "effect_measure": "OR",
                "effect_value": 2.5,
            }
        }
        errors = self.agent.validate(data)
        assert len(errors) > 0

    def test_compute_or_from_table(self):
        data = {
            "analysis": {
                "effect_measure": "OR",
                "two_by_two_table": {
                    "a": 150, "b": 350, "c": 30, "d": 470
                }
            }
        }
        result = self.agent.compute_effect_size(data)
        expected_or = (150 * 470) / (350 * 30)
        assert result["analysis"]["effect_value"] == pytest.approx(expected_or, rel=1e-3)

    def test_compute_rr_from_table(self):
        data = {
            "analysis": {
                "effect_measure": "RR",
                "two_by_two_table": {
                    "a": 150, "b": 350, "c": 30, "d": 470
                }
            }
        }
        result = self.agent.compute_effect_size(data)
        expected_rr = (150 / 500) / (30 / 500)
        assert result["analysis"]["effect_value"] == pytest.approx(expected_rr, rel=1e-3)

    def test_continuity_correction(self):
        data = {
            "analysis": {
                "effect_measure": "OR",
                "two_by_two_table": {
                    "a": 10, "b": 0, "c": 5, "d": 100
                }
            }
        }
        result = self.agent.compute_effect_size(data)
        # With 0.5 correction: a=10.5, b=0.5, c=5.5, d=100.5
        expected = (10.5 * 100.5) / (0.5 * 5.5)
        assert result["analysis"]["effect_value"] == pytest.approx(expected, rel=1e-3)


class TestMDSMDAgent:
    """Test MDSMDAgent validation and computation."""

    def setup_method(self):
        self.agent = MDSMDAgent()

    def test_validate_complete_effect_value(self):
        data = {
            "analysis": {
                "effect_measure": "MD",
                "effect_value": 5.2,
                "ci_lower": 2.1,
                "ci_upper": 8.3,
            }
        }
        errors = self.agent.validate(data)
        assert len(errors) == 0

    def test_validate_complete_continuous_data(self):
        data = {
            "analysis": {
                "effect_measure": "SMD",
                "continuous_data": {
                    "exposed_mean": 142.5, "exposed_sd": 12.3, "exposed_n": 150,
                    "control_mean": 137.3, "control_sd": 11.8, "control_n": 150
                }
            }
        }
        errors = self.agent.validate(data)
        assert len(errors) == 0

    def test_compute_md(self):
        data = {
            "analysis": {
                "effect_measure": "MD",
                "continuous_data": {
                    "exposed_mean": 142.5, "exposed_sd": 12.3, "exposed_n": 150,
                    "control_mean": 137.3, "control_sd": 11.8, "control_n": 150
                }
            }
        }
        result = self.agent.compute_effect_size(data)
        assert result["analysis"]["effect_value"] == pytest.approx(5.2, rel=1e-3)

    def test_compute_smd(self):
        data = {
            "analysis": {
                "effect_measure": "SMD",
                "continuous_data": {
                    "exposed_mean": 142.5, "exposed_sd": 12.3, "exposed_n": 150,
                    "control_mean": 137.3, "control_sd": 11.8, "control_n": 150
                }
            }
        }
        result = self.agent.compute_effect_size(data)
        smd = result["analysis"]["effect_value"]
        assert smd is not None
        assert smd > 0


class TestHRAgent:
    """Test HRAgent validation and computation."""

    def setup_method(self):
        self.agent = HRAgent()

    def test_validate_complete_effect_value(self):
        data = {
            "analysis": {
                "effect_measure": "HR",
                "effect_value": 1.75,
                "ci_lower": 1.32,
                "ci_upper": 2.31,
            }
        }
        errors = self.agent.validate(data)
        assert len(errors) == 0

    def test_validate_complete_survival_data(self):
        data = {
            "analysis": {
                "effect_measure": "HR",
                "survival_data": {
                    "events_exposed": 120,
                    "events_control": 80,
                    "person_time_exposed": 4500.5,
                    "person_time_control": 5200.0,
                }
            }
        }
        errors = self.agent.validate(data)
        assert len(errors) == 0

    def test_compute_hr_from_survival_data(self):
        data = {
            "analysis": {
                "effect_measure": "HR",
                "survival_data": {
                    "events_exposed": 120,
                    "events_control": 80,
                    "person_time_exposed": 4500.5,
                    "person_time_control": 5200.0,
                }
            }
        }
        result = self.agent.compute_effect_size(data)
        expected_hr = (120 / 4500.5) / (80 / 5200.0)
        assert result["analysis"]["effect_value"] == pytest.approx(expected_hr, rel=1e-3)

    def test_compute_hr_from_rates(self):
        data = {
            "analysis": {
                "effect_measure": "HR",
                "survival_data": {
                    "rate_exposed": 0.0267,
                    "rate_control": 0.0154,
                }
            }
        }
        result = self.agent.compute_effect_size(data)
        assert result["analysis"]["effect_value"] == pytest.approx(0.0267 / 0.0154, rel=1e-3)


class TestAgentFactory:
    """Test agent factory functions."""

    def test_get_agent_proportion(self):
        agent = get_agent("PROPORTION")
        assert isinstance(agent, ProportionAgent)

    def test_get_agent_or(self):
        agent = get_agent("OR")
        assert isinstance(agent, ORRRAgent)

    def test_get_agent_invalid(self):
        assert get_agent("INVALID") is None

    def test_process_with_agent(self):
        data = {
            "analysis": {
                "proportion_data": {
                    "events": 45,
                    "sample_size": 300,
                }
            }
        }
        result = process_with_agent("PROPORTION", data)
        assert "proportion" in result["analysis"]["proportion_data"]

    def test_process_with_invalid_agent(self):
        data = {"analysis": {"effect_value": 2.5}}
        result = process_with_agent("INVALID", data)
        assert result == data  # Should return unchanged

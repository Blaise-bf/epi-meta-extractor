"""Agent for HR effect size validation and computation."""

from typing import Dict, Any, List
from backend.services.agents.base_agent import BaseExtractionAgent


class HRAgent(BaseExtractionAgent):
    """Agent for hazard ratio validation and computation."""

    def __init__(self):
        super().__init__("HR")

    def validate(self, extracted_data: Dict[str, Any]) -> List[str]:
        """Validate HR data.

        Requires either:
        - effect_value + CI, OR
        - survival_data (events + person-time for both groups)
        """
        errors = []
        analysis = extracted_data.get("analysis", {})

        effect_value = analysis.get("effect_value")
        ci_lower = analysis.get("ci_lower")
        ci_upper = analysis.get("ci_upper")
        survival_data = analysis.get("survival_data")

        # Check if primary data (effect_value + CI) is present
        has_primary = effect_value is not None and ci_lower is not None and ci_upper is not None

        # Check if alternative data (survival_data) is present
        has_alternative = False
        if survival_data and isinstance(survival_data, dict):
            required_keys = [
                "events_exposed", "events_control",
                "person_time_exposed", "person_time_control"
            ]
            has_alternative = all(survival_data.get(k) is not None for k in required_keys)

        if not has_primary and not has_alternative:
            errors.append(
                "HR data incomplete. Need either (effect_value + CI_lower + CI_upper) "
                "or (survival_data with events and person-time for both groups)"
            )

        # Validate survival_data values
        if survival_data and isinstance(survival_data, dict):
            for key in ["events_exposed", "events_control"]:
                val = survival_data.get(key)
                if val is not None and val < 0:
                    errors.append(f"{key} must be >= 0")
            for key in ["person_time_exposed", "person_time_control"]:
                val = survival_data.get(key)
                if val is not None and val < 0:
                    errors.append(f"{key} must be >= 0")

        # Validate CI bounds
        if ci_lower is not None and ci_upper is not None and ci_lower > ci_upper:
            errors.append("ci_lower must be <= ci_upper")

        return errors

    def compute_effect_size(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute HR from survival data (events + person-time) if effect_value is missing."""
        analysis = extracted_data.get("analysis", {})
        effect_value = analysis.get("effect_value")
        survival_data = analysis.get("survival_data")

        if effect_value is not None or not survival_data or not isinstance(survival_data, dict):
            return extracted_data

        events_exposed = survival_data.get("events_exposed")
        events_control = survival_data.get("events_control")
        person_time_exposed = survival_data.get("person_time_exposed")
        person_time_control = survival_data.get("person_time_control")
        rate_exposed = survival_data.get("rate_exposed")
        rate_control = survival_data.get("rate_control")

        # Use pre-computed rates if available
        if rate_exposed is not None and rate_control is not None and rate_control > 0:
            computed_hr = rate_exposed / rate_control
            analysis["effect_value"] = round(computed_hr, 4)
            return extracted_data

        # Compute rates from events and person-time
        if (
            events_exposed is not None and person_time_exposed is not None and person_time_exposed > 0
            and events_control is not None and person_time_control is not None and person_time_control > 0
        ):
            rate_e = events_exposed / person_time_exposed
            rate_c = events_control / person_time_control
            if rate_c > 0:
                computed_hr = rate_e / rate_c
                analysis["effect_value"] = round(computed_hr, 4)
                survival_data["rate_exposed"] = round(rate_e, 6)
                survival_data["rate_control"] = round(rate_c, 6)

        return extracted_data

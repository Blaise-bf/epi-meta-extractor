"""Agent for MD / SMD effect size validation and computation."""

import math
from typing import Dict, Any, List
from backend.services.agents.base_agent import BaseExtractionAgent


class MDSMDAgent(BaseExtractionAgent):
    """Agent for mean difference and standardized mean difference validation and computation."""

    def __init__(self):
        super().__init__("MD_SMD")

    def validate(self, extracted_data: Dict[str, Any]) -> List[str]:
        """Validate MD/SMD data.

        Requires either:
        - effect_value + CI, OR
        - complete continuous_data (mean, sd, n for both groups)
        """
        errors = []
        analysis = extracted_data.get("analysis", {})

        effect_value = analysis.get("effect_value")
        ci_lower = analysis.get("ci_lower")
        ci_upper = analysis.get("ci_upper")
        continuous_data = analysis.get("continuous_data")

        # Check if primary data (effect_value + CI) is present
        has_primary = effect_value is not None and ci_lower is not None and ci_upper is not None

        # Check if alternative data (continuous_data) is present
        has_alternative = False
        if continuous_data and isinstance(continuous_data, dict):
            required_keys = [
                "exposed_mean", "exposed_sd", "exposed_n",
                "control_mean", "control_sd", "control_n"
            ]
            has_alternative = all(continuous_data.get(k) is not None for k in required_keys)

        if not has_primary and not has_alternative:
            errors.append(
                "MD/SMD data incomplete. Need either (effect_value + CI_lower + CI_upper) "
                "or (complete continuous_data with means, SDs, and Ns for both groups)"
            )

        # Validate continuous_data values
        if continuous_data and isinstance(continuous_data, dict):
            for key in ["exposed_sd", "control_sd"]:
                val = continuous_data.get(key)
                if val is not None and val < 0:
                    errors.append(f"{key} must be >= 0")
            for key in ["exposed_n", "control_n"]:
                val = continuous_data.get(key)
                if val is not None and val < 1:
                    errors.append(f"{key} must be >= 1")

        # Validate CI bounds
        if ci_lower is not None and ci_upper is not None and ci_lower > ci_upper:
            errors.append("ci_lower must be <= ci_upper")

        return errors

    def compute_effect_size(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute MD or SMD from group-level continuous data if effect_value is missing."""
        analysis = extracted_data.get("analysis", {})
        effect_measure = analysis.get("effect_measure")
        effect_value = analysis.get("effect_value")
        continuous_data = analysis.get("continuous_data")

        if effect_value is not None or not continuous_data or not isinstance(continuous_data, dict):
            return extracted_data

        exposed_mean = continuous_data.get("exposed_mean")
        exposed_sd = continuous_data.get("exposed_sd")
        exposed_n = continuous_data.get("exposed_n")
        control_mean = continuous_data.get("control_mean")
        control_sd = continuous_data.get("control_sd")
        control_n = continuous_data.get("control_n")

        if exposed_mean is None or control_mean is None:
            return extracted_data

        # Compute MD
        md = exposed_mean - control_mean

        if effect_measure == "MD":
            analysis["effect_value"] = round(md, 4)
        elif effect_measure == "SMD":
            # Compute Cohen's d
            if exposed_sd is not None and control_sd is not None and exposed_n is not None and control_n is not None:
                n1 = exposed_n
                n2 = control_n
                pooled_sd = math.sqrt(
                    ((n1 - 1) * exposed_sd ** 2 + (n2 - 1) * control_sd ** 2)
                    / (n1 + n2 - 2)
                )
                if pooled_sd > 0:
                    smd = md / pooled_sd
                    analysis["effect_value"] = round(smd, 4)

        return extracted_data

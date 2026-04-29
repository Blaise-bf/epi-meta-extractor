"""Agent for proportion effect size validation and computation."""

import math
from typing import Dict, Any, List
from backend.services.agents.base_agent import BaseExtractionAgent


class ProportionAgent(BaseExtractionAgent):
    """Agent for proportion data validation and computation."""

    def __init__(self):
        super().__init__("PROPORTION")

    def validate(self, extracted_data: Dict[str, Any]) -> List[str]:
        """Validate proportion data.

        Requires either:
        - events + sample_size, OR
        - proportion + se (or CI)
        """
        errors = []
        analysis = extracted_data.get("analysis", {})
        proportion_data = analysis.get("proportion_data")

        if not proportion_data:
            errors.append("Missing proportion_data block")
            return errors

        events = proportion_data.get("events")
        sample_size = proportion_data.get("sample_size")
        proportion = proportion_data.get("proportion")
        se = proportion_data.get("se")
        ci_lower = proportion_data.get("ci_lower")
        ci_upper = proportion_data.get("ci_upper")

        # Check if primary data (events + sample_size) is present
        has_primary = events is not None and sample_size is not None

        # Check if alternative data (proportion + se/CI) is present
        has_alternative = proportion is not None and (se is not None or (ci_lower is not None and ci_upper is not None))

        if not has_primary and not has_alternative:
            errors.append(
                "Proportion data incomplete. Need either (events + sample_size) "
                "or (proportion + se/CI)"
            )

        # Validate values
        if events is not None and events < 0:
            errors.append("events must be >= 0")
        if sample_size is not None and sample_size < 1:
            errors.append("sample_size must be >= 1")
        if proportion is not None and not (0 <= proportion <= 1):
            errors.append("proportion must be between 0 and 1")
        if se is not None and se < 0:
            errors.append("se must be >= 0")
        if ci_lower is not None and ci_upper is not None and ci_lower > ci_upper:
            errors.append("ci_lower must be <= ci_upper")

        return errors

    def compute_effect_size(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute derived proportion fields.

        - If events + sample_size are present but proportion is missing, compute proportion.
        - If proportion + sample_size are present but se is missing, compute se.
        """
        analysis = extracted_data.get("analysis", {})
        proportion_data = analysis.get("proportion_data")

        if not proportion_data:
            return extracted_data

        events = proportion_data.get("events")
        sample_size = proportion_data.get("sample_size")
        proportion = proportion_data.get("proportion")
        se = proportion_data.get("se")

        # Compute proportion from events / sample_size
        if proportion is None and events is not None and sample_size is not None and sample_size > 0:
            proportion_data["proportion"] = events / sample_size
            proportion = proportion_data["proportion"]

        # Compute se from proportion and sample_size
        if se is None and proportion is not None and sample_size is not None and sample_size > 0:
            proportion_data["se"] = math.sqrt(proportion * (1 - proportion) / sample_size)
            se = proportion_data["se"]

        # Compute CI from proportion and se if CI is missing
        ci_lower = proportion_data.get("ci_lower")
        ci_upper = proportion_data.get("ci_upper")
        if ci_lower is None and ci_upper is None and proportion is not None and se is not None:
            z = 1.96  # 95% CI
            proportion_data["ci_lower"] = max(0, proportion - z * se)
            proportion_data["ci_upper"] = min(1, proportion + z * se)

        return extracted_data

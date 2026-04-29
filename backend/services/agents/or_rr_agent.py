"""Agent for OR / RR effect size validation and computation."""

from typing import Dict, Any, List
from backend.services.agents.base_agent import BaseExtractionAgent


class ORRRAgent(BaseExtractionAgent):
    """Agent for odds ratio and risk ratio validation and computation."""

    def __init__(self):
        super().__init__("OR_RR")

    def validate(self, extracted_data: Dict[str, Any]) -> List[str]:
        """Validate OR/RR data.

        Requires either:
        - effect_value + CI, OR
        - complete 2×2 table (a, b, c, d)
        """
        errors = []
        analysis = extracted_data.get("analysis", {})

        effect_value = analysis.get("effect_value")
        ci_lower = analysis.get("ci_lower")
        ci_upper = analysis.get("ci_upper")
        two_by_two = analysis.get("two_by_two_table")

        # Check if primary data (effect_value + CI) is present
        has_primary = effect_value is not None and ci_lower is not None and ci_upper is not None

        # Check if alternative data (2×2 table) is present
        has_alternative = False
        if two_by_two and isinstance(two_by_two, dict):
            has_alternative = all(
                two_by_two.get(k) is not None for k in ["a", "b", "c", "d"]
            )

        if not has_primary and not has_alternative:
            errors.append(
                "OR/RR data incomplete. Need either (effect_value + CI_lower + CI_upper) "
                "or (complete 2×2 table with a, b, c, d)"
            )

        # Validate 2×2 table cells
        if two_by_two and isinstance(two_by_two, dict):
            for cell in ["a", "b", "c", "d"]:
                val = two_by_two.get(cell)
                if val is not None and val < 0:
                    errors.append(f"2×2 table cell '{cell}' must be >= 0")

        # Validate CI bounds
        if ci_lower is not None and ci_upper is not None and ci_lower > ci_upper:
            errors.append("ci_lower must be <= ci_upper")

        return errors

    def compute_effect_size(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute OR/RR from 2×2 table if effect_value is missing.

        Also adds continuity correction if any cell is zero.
        """
        analysis = extracted_data.get("analysis", {})
        effect_measure = analysis.get("effect_measure")
        effect_value = analysis.get("effect_value")
        two_by_two = analysis.get("two_by_two_table")

        if effect_value is not None or not two_by_two or not isinstance(two_by_two, dict):
            return extracted_data

        a = two_by_two.get("a")
        b = two_by_two.get("b")
        c = two_by_two.get("c")
        d = two_by_two.get("d")

        if a is None or b is None or c is None or d is None:
            return extracted_data

        # Apply continuity correction if any cell is zero
        if a == 0 or b == 0 or c == 0 or d == 0:
            a, b, c, d = a + 0.5, b + 0.5, c + 0.5, d + 0.5

        if effect_measure == "OR":
            computed_or = (a * d) / (b * c)
            analysis["effect_value"] = round(computed_or, 4)
        elif effect_measure == "RR":
            if a + b > 0 and c + d > 0:
                computed_rr = (a / (a + b)) / (c / (c + d))
                analysis["effect_value"] = round(computed_rr, 4)

        return extracted_data

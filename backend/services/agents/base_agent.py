"""Base class for effect-size-specific extraction agents.

Agents validate extracted data and compute derived fields (e.g., proportion from events/sample_size).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseExtractionAgent(ABC):
    """Base class for effect-size-specific extraction agents."""

    def __init__(self, effect_type: str):
        self.effect_type = effect_type.upper()

    @abstractmethod
    def validate(self, extracted_data: Dict[str, Any]) -> List[str]:
        """Validate extracted data for this effect size.

        Returns:
            List of validation error messages. Empty list if valid.
        """
        pass

    @abstractmethod
    def compute_effect_size(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute derived fields (e.g., proportion from events/sample_size).

        Returns:
            Updated extracted_data with computed fields.
        """
        pass

    def format_for_export(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format extracted data for CSV export.

        Returns:
            Flattened dictionary ready for CSV export.
        """
        return extracted_data

    def should_retry(self, extracted_data: Dict[str, Any]) -> bool:
        """Determine if extraction should be retried based on missing critical fields.

        Returns:
            True if re-extraction should be attempted.
        """
        errors = self.validate(extracted_data)
        return len(errors) > 0

    def _get_nested(self, data: Dict[str, Any], path: str) -> Any:
        """Get nested dict value by dot notation."""
        keys = path.split(".")
        val = data
        for key in keys:
            if isinstance(val, dict):
                val = val.get(key)
            else:
                return None
        return val

    def _set_nested(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """Set nested dict value by dot notation."""
        keys = path.split(".")
        val = data
        for key in keys[:-1]:
            if key not in val or not isinstance(val[key], dict):
                val[key] = {}
            val = val[key]
        val[keys[-1]] = value

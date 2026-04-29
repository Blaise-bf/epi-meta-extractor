"""Agent factory and registry for effect-size-specific extraction agents."""

from typing import Dict, Any, Optional, Type
from backend.services.agents.base_agent import BaseExtractionAgent
from backend.services.agents.proportion_agent import ProportionAgent
from backend.services.agents.or_rr_agent import ORRRAgent
from backend.services.agents.md_smd_agent import MDSMDAgent
from backend.services.agents.hr_agent import HRAgent

# Registry mapping effect measures to agent classes
AGENT_REGISTRY: Dict[str, Type[BaseExtractionAgent]] = {
    "PROPORTION": ProportionAgent,
    "OR": ORRRAgent,
    "RR": ORRRAgent,
    "MD": MDSMDAgent,
    "SMD": MDSMDAgent,
    "HR": HRAgent,
}


def get_agent(effect_type: str) -> Optional[BaseExtractionAgent]:
    """Get the appropriate agent for a given effect measure.

    Args:
        effect_type: One of PROPORTION, OR, RR, MD, SMD, HR

    Returns:
        Agent instance, or None if effect_type is not recognized.
    """
    agent_class = AGENT_REGISTRY.get(effect_type.upper())
    if agent_class:
        return agent_class()
    return None


def process_with_agent(
    effect_type: str,
    extracted_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Process extracted data with the appropriate agent.

    This is a convenience function that:
    1. Gets the appropriate agent
    2. Validates the data
    3. Computes derived fields
    4. Returns the enriched data

    Args:
        effect_type: One of PROPORTION, OR, RR, MD, SMD, HR
        extracted_data: The extracted study data

    Returns:
        Enriched extracted data with computed fields.
    """
    agent = get_agent(effect_type)
    if not agent:
        return extracted_data

    # Validate
    errors = agent.validate(extracted_data)
    if errors:
        print(f"Validation errors for {effect_type}: {errors}")

    # Compute derived fields
    enriched_data = agent.compute_effect_size(extracted_data)

    return enriched_data


__all__ = [
    "BaseExtractionAgent",
    "ProportionAgent",
    "ORRRAgent",
    "MDSMDAgent",
    "HRAgent",
    "AGENT_REGISTRY",
    "get_agent",
    "process_with_agent",
]

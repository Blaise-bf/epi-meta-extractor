"""Prompts package for effect-size-specific and section-specific extraction."""

from backend.services.prompts.base_prompt import (
    BASE_SYSTEM_MESSAGE,
    CRITICAL_RULES,
    FLEXIBLE_MATCHING_RULES,
)
from backend.services.prompts.metadata_prompt import (
    METADATA_EXTRACTION_PROMPT,
    METADATA_SYSTEM_MESSAGE,
)
from backend.services.prompts.methods_prompt import (
    METHODS_EXTRACTION_PROMPT,
    METHODS_SYSTEM_MESSAGE,
)
from backend.services.prompts.analysis_prompt import (
    ANALYSIS_EXTRACTION_PROMPT,
    ANALYSIS_SYSTEM_MESSAGE,
)
from backend.services.prompts.proportion_prompt import (
    PROPORTION_EXTRACTION_PROMPT,
    PROPORTION_SYSTEM_MESSAGE,
)
from backend.services.prompts.or_rr_prompt import (
    OR_RR_EXTRACTION_PROMPT,
    OR_RR_SYSTEM_MESSAGE,
)
from backend.services.prompts.md_smd_prompt import (
    MD_SMD_EXTRACTION_PROMPT,
    MD_SMD_SYSTEM_MESSAGE,
)
from backend.services.prompts.hr_prompt import (
    HR_EXTRACTION_PROMPT,
    HR_SYSTEM_MESSAGE,
)

# Mapping of effect measures to their analysis prompts
EFFECT_PROMPT_MAP = {
    "PROPORTION": (PROPORTION_EXTRACTION_PROMPT, PROPORTION_SYSTEM_MESSAGE),
    "OR": (OR_RR_EXTRACTION_PROMPT, OR_RR_SYSTEM_MESSAGE),
    "RR": (OR_RR_EXTRACTION_PROMPT, OR_RR_SYSTEM_MESSAGE),
    "MD": (MD_SMD_EXTRACTION_PROMPT, MD_SMD_SYSTEM_MESSAGE),
    "SMD": (MD_SMD_EXTRACTION_PROMPT, MD_SMD_SYSTEM_MESSAGE),
    "HR": (HR_EXTRACTION_PROMPT, HR_SYSTEM_MESSAGE),
}


def get_effect_prompt(effect_type: str):
    """Get the extraction prompt and system message for a given effect measure.

    Args:
        effect_type: One of PROPORTION, OR, RR, MD, SMD, HR

    Returns:
        Tuple of (extraction_prompt, system_message). Falls back to generic analysis prompt
        if effect_type is not recognized.
    """
    return EFFECT_PROMPT_MAP.get(
        effect_type.upper(),
        (ANALYSIS_EXTRACTION_PROMPT, ANALYSIS_SYSTEM_MESSAGE),
    )


__all__ = [
    "BASE_SYSTEM_MESSAGE",
    "CRITICAL_RULES",
    "FLEXIBLE_MATCHING_RULES",
    "METADATA_EXTRACTION_PROMPT",
    "METADATA_SYSTEM_MESSAGE",
    "METHODS_EXTRACTION_PROMPT",
    "METHODS_SYSTEM_MESSAGE",
    "ANALYSIS_EXTRACTION_PROMPT",
    "ANALYSIS_SYSTEM_MESSAGE",
    "PROPORTION_EXTRACTION_PROMPT",
    "PROPORTION_SYSTEM_MESSAGE",
    "OR_RR_EXTRACTION_PROMPT",
    "OR_RR_SYSTEM_MESSAGE",
    "MD_SMD_EXTRACTION_PROMPT",
    "MD_SMD_SYSTEM_MESSAGE",
    "HR_EXTRACTION_PROMPT",
    "HR_SYSTEM_MESSAGE",
    "EFFECT_PROMPT_MAP",
    "get_effect_prompt",
]

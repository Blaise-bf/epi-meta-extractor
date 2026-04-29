"""Tests for effect-size-specific prompts."""

import pytest
from backend.services.prompts import (
    get_effect_prompt,
    EFFECT_PROMPT_MAP,
    METADATA_EXTRACTION_PROMPT,
    METHODS_EXTRACTION_PROMPT,
    ANALYSIS_EXTRACTION_PROMPT,
)
from backend.services.prompts.proportion_prompt import PROPORTION_EXTRACTION_PROMPT
from backend.services.prompts.or_rr_prompt import OR_RR_EXTRACTION_PROMPT
from backend.services.prompts.md_smd_prompt import MD_SMD_EXTRACTION_PROMPT
from backend.services.prompts.hr_prompt import HR_EXTRACTION_PROMPT


class TestGetEffectPrompt:
    """Test prompt factory function."""

    def test_proportion_prompt(self):
        prompt, system_msg = get_effect_prompt("PROPORTION")
        assert prompt == PROPORTION_EXTRACTION_PROMPT
        assert "proportion" in system_msg.lower()

    def test_or_prompt(self):
        prompt, system_msg = get_effect_prompt("OR")
        assert prompt == OR_RR_EXTRACTION_PROMPT
        assert "odds ratio" in system_msg.lower()

    def test_rr_prompt(self):
        prompt, system_msg = get_effect_prompt("RR")
        assert prompt == OR_RR_EXTRACTION_PROMPT

    def test_md_prompt(self):
        prompt, system_msg = get_effect_prompt("MD")
        assert prompt == MD_SMD_EXTRACTION_PROMPT
        assert "mean difference" in system_msg.lower()

    def test_smd_prompt(self):
        prompt, system_msg = get_effect_prompt("SMD")
        assert prompt == MD_SMD_EXTRACTION_PROMPT

    def test_hr_prompt(self):
        prompt, system_msg = get_effect_prompt("HR")
        assert prompt == HR_EXTRACTION_PROMPT
        assert "hazard ratio" in system_msg.lower()

    def test_invalid_fallback(self):
        prompt, system_msg = get_effect_prompt("INVALID")
        assert prompt == ANALYSIS_EXTRACTION_PROMPT

    def test_case_insensitive(self):
        prompt, system_msg = get_effect_prompt("proportion")
        assert prompt == PROPORTION_EXTRACTION_PROMPT


class TestPromptContent:
    """Test that prompts contain expected content."""

    def test_proportion_prompt_has_events_field(self):
        assert '"events"' in PROPORTION_EXTRACTION_PROMPT
        assert '"sample_size"' in PROPORTION_EXTRACTION_PROMPT

    def test_or_rr_prompt_has_two_by_two(self):
        assert '"two_by_two_table"' in OR_RR_EXTRACTION_PROMPT
        assert '"a"' in OR_RR_EXTRACTION_PROMPT

    def test_md_smd_prompt_has_continuous_data(self):
        assert '"continuous_data"' in MD_SMD_EXTRACTION_PROMPT
        assert '"exposed_mean"' in MD_SMD_EXTRACTION_PROMPT

    def test_hr_prompt_has_survival_data(self):
        assert '"survival_data"' in HR_EXTRACTION_PROMPT
        assert '"events_exposed"' in HR_EXTRACTION_PROMPT

    def test_metadata_prompt_has_country(self):
        assert '"country"' in METADATA_EXTRACTION_PROMPT
        assert '"continent"' in METADATA_EXTRACTION_PROMPT

    def test_methods_prompt_has_definitions(self):
        assert '"exposure_definition"' in METHODS_EXTRACTION_PROMPT
        assert '"outcome_definition"' in METHODS_EXTRACTION_PROMPT

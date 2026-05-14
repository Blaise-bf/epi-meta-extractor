"""CSV Export service for epidemiologic study data"""

import csv
import io
from typing import List, Dict, Any, Optional


class CSVExportService:
    """Handle CSV export of extracted study data"""

    # Define all fields based on the structured output schemas
    # (MetadataOutput, MethodsOutput, ORRRAnalysisOutput, HRAnalysisOutput,
    #  MDSMDAnalysisOutput, ProportionAnalysisOutput)
    FIELD_MAPPING = {
        # Metadata fields
        "study_id": "study_id",
        "title": "title",
        "authors": "authors",
        "year": "year",
        "journal": "journal",
        "country": "country",
        "continent": "continent",

        # Methods fields
        "study_design": "study_design",
        "population": "population",
        "sample_size": "sample_size",
        "exposure_definition": "exposure_definition",
        "outcome_definition": "outcome_definition",

        # Analysis fields
        "exposure": "exposure",
        "outcome": "outcome",
        "effect_measure": "effect_measure",
        "effect_value": "effect_value",
        "ci_lower": "ci_lower",
        "ci_upper": "ci_upper",
        "p_value": "p_value",
        "adjustment_variables": "adjustment_variables",

        # Proportion-specific fields
        "proportion_events": "proportion_events",
        "proportion_sample_size": "proportion_sample_size",
        "proportion": "proportion",
        "proportion_se": "proportion_se",
        "proportion_ci_lower": "proportion_ci_lower",
        "proportion_ci_upper": "proportion_ci_upper",

        # 2×2 table fields (for OR/RR)
        "two_by_two_a": "two_by_two_a",
        "two_by_two_b": "two_by_two_b",
        "two_by_two_c": "two_by_two_c",
        "two_by_two_d": "two_by_two_d",

        # Continuous data fields (for MD/SMD)
        "exposed_mean": "exposed_mean",
        "exposed_sd": "exposed_sd",
        "exposed_n": "exposed_n",
        "control_mean": "control_mean",
        "control_sd": "control_sd",
        "control_n": "control_n",

        # Survival data fields (for HR)
        "events_exposed": "events_exposed",
        "events_control": "events_control",
        "person_time_exposed": "person_time_exposed",
        "person_time_control": "person_time_control",
        "rate_exposed": "rate_exposed",
        "rate_control": "rate_control",

        # Group statistics (flattened) — used by OR/RR structured output
        "unexposed_n": "unexposed_n",
        "unexposed_mean": "unexposed_mean",
        "unexposed_sd": "unexposed_sd",

        # Additional fields
        "effect_measure_type": "effect_measure_type",
    }

    def _flatten_group_statistics(self, group_stats: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Flatten nested group statistics into flat structure"""
        flat = {}
        if not group_stats:
            return flat

        if "exposed" in group_stats:
            exposed = group_stats["exposed"]
            flat["exposed_n"] = exposed.get("n")
            flat["exposed_mean"] = exposed.get("mean")
            flat["exposed_sd"] = exposed.get("sd")

        if "unexposed" in group_stats:
            unexposed = group_stats["unexposed"]
            flat["unexposed_n"] = unexposed.get("n")
            flat["unexposed_mean"] = unexposed.get("mean")
            flat["unexposed_sd"] = unexposed.get("sd")

        return flat

    def _flatten_study(self, study: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested study structure into flat dictionary"""
        flat = {}

        # Extract metadata fields
        metadata = study.get("metadata", {})
        if metadata:
            flat["study_id"] = metadata.get("study_id")
            flat["title"] = metadata.get("title")
            flat["authors"] = metadata.get("authors")
            flat["year"] = metadata.get("year")
            flat["journal"] = metadata.get("journal")
            flat["country"] = metadata.get("country")
            flat["continent"] = metadata.get("continent")

        # Extract methods fields
        methods = study.get("methods", {})
        if methods:
            flat["study_design"] = methods.get("study_design")
            flat["population"] = methods.get("population")
            flat["sample_size"] = methods.get("sample_size")
            flat["exposure_definition"] = methods.get("exposure_definition")
            flat["outcome_definition"] = methods.get("outcome_definition")

        # Extract analysis fields
        analysis = study.get("analysis", {})
        if analysis:
            flat["exposure"] = analysis.get("exposure")
            flat["outcome"] = analysis.get("outcome")
            flat["effect_measure"] = analysis.get("effect_measure")
            flat["effect_value"] = analysis.get("effect_value")
            flat["ci_lower"] = analysis.get("ci_lower")
            flat["ci_upper"] = analysis.get("ci_upper")
            flat["p_value"] = analysis.get("p_value")

            # Handle adjustment variables (list to string)
            adj_vars = analysis.get("adjustment_variables")
            if adj_vars:
                flat["adjustment_variables"] = "; ".join(adj_vars)

            # Flatten group statistics
            group_stats = analysis.get("group_statistics")
            flat.update(self._flatten_group_statistics(group_stats))

            # Flatten proportion data
            proportion_data = analysis.get("proportion_data")
            if proportion_data:
                flat["proportion_events"] = proportion_data.get("events")
                flat["proportion_sample_size"] = proportion_data.get("sample_size")
                flat["proportion"] = proportion_data.get("proportion")
                flat["proportion_se"] = proportion_data.get("se")
                flat["proportion_ci_lower"] = proportion_data.get("ci_lower")
                flat["proportion_ci_upper"] = proportion_data.get("ci_upper")

            # Flatten 2×2 table
            two_by_two = analysis.get("two_by_two_table")
            if two_by_two:
                flat["two_by_two_a"] = two_by_two.get("a")
                flat["two_by_two_b"] = two_by_two.get("b")
                flat["two_by_two_c"] = two_by_two.get("c")
                flat["two_by_two_d"] = two_by_two.get("d")

            # Flatten continuous data
            continuous_data = analysis.get("continuous_data")
            if continuous_data:
                flat["exposed_mean"] = continuous_data.get("exposed_mean")
                flat["exposed_sd"] = continuous_data.get("exposed_sd")
                flat["exposed_n"] = continuous_data.get("exposed_n")
                flat["control_mean"] = continuous_data.get("control_mean")
                flat["control_sd"] = continuous_data.get("control_sd")
                flat["control_n"] = continuous_data.get("control_n")

            # Flatten survival data
            survival_data = analysis.get("survival_data")
            if survival_data:
                flat["events_exposed"] = survival_data.get("events_exposed")
                flat["events_control"] = survival_data.get("events_control")
                flat["person_time_exposed"] = survival_data.get("person_time_exposed")
                flat["person_time_control"] = survival_data.get("person_time_control")
                flat["rate_exposed"] = survival_data.get("rate_exposed")
                flat["rate_control"] = survival_data.get("rate_control")

        # Add effect measure type
        flat["effect_measure_type"] = study.get("effect_measure_type")

        # Remove MongoDB _id if present
        flat.pop("_id", None)

        return flat

    def export_to_csv(self, studies: List[Dict[str, Any]]) -> str:
        """
        Export studies to CSV format

        Args:
            studies: List of study dictionaries

        Returns:
            CSV string
        """
        if not studies:
            return ""

        # Flatten all studies
        flat_studies = [self._flatten_study(study) for study in studies]

        # Get all unique keys to build CSV header
        all_keys = set()
        for study in flat_studies:
            all_keys.update(study.keys())

        # Order fields based on FIELD_MAPPING with any extras at the end
        ordered_keys = [
            key for key in self.FIELD_MAPPING.keys()
            if key in all_keys
        ]
        # Add any extra keys not in mapping
        ordered_keys.extend(sorted(all_keys - set(self.FIELD_MAPPING.keys())))

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=ordered_keys)

        # Write header
        writer.writeheader()

        # Write data rows
        for study in flat_studies:
            # Fill in empty fields with None for missing keys
            row = {key: study.get(key) for key in ordered_keys}
            writer.writerow(row)

        return output.getvalue()

    def export_to_csv_bytes(self, studies: List[Dict[str, Any]]) -> bytes:
        """
        Export studies to CSV bytes

        Args:
            studies: List of study dictionaries

        Returns:
            CSV content as bytes
        """
        csv_content = self.export_to_csv(studies)
        return csv_content.encode('utf-8')


# Global instance
csv_export_service = CSVExportService()

import hashlib
from typing import Dict, Any, List, Tuple
from backend.models.schemas import ExtractedStudy, ExtractionQuality, Analysis, EffectMeasure


# Effect-size-specific required fields
EFFECT_REQUIRED_FIELDS = {
    "PROPORTION": {
        "primary": ["analysis.proportion_data.events", "analysis.proportion_data.sample_size"],
        "alternative": ["analysis.proportion_data.proportion", "analysis.proportion_data.se"],
        "fields": ["analysis.proportion_data.events", "analysis.proportion_data.sample_size",
                   "analysis.proportion_data.proportion", "analysis.proportion_data.se",
                   "analysis.proportion_data.ci_lower", "analysis.proportion_data.ci_upper"],
    },
    "OR": {
        "primary": ["analysis.effect_value", "analysis.ci_lower", "analysis.ci_upper"],
        "alternative": ["analysis.two_by_two_table.a", "analysis.two_by_two_table.b",
                        "analysis.two_by_two_table.c", "analysis.two_by_two_table.d"],
        "fields": ["analysis.effect_value", "analysis.ci_lower", "analysis.ci_upper",
                   "analysis.two_by_two_table.a", "analysis.two_by_two_table.b",
                   "analysis.two_by_two_table.c", "analysis.two_by_two_table.d"],
    },
    "RR": {
        "primary": ["analysis.effect_value", "analysis.ci_lower", "analysis.ci_upper"],
        "alternative": ["analysis.two_by_two_table.a", "analysis.two_by_two_table.b",
                        "analysis.two_by_two_table.c", "analysis.two_by_two_table.d"],
        "fields": ["analysis.effect_value", "analysis.ci_lower", "analysis.ci_upper",
                   "analysis.two_by_two_table.a", "analysis.two_by_two_table.b",
                   "analysis.two_by_two_table.c", "analysis.two_by_two_table.d"],
    },
    "MD": {
        "primary": ["analysis.effect_value", "analysis.ci_lower", "analysis.ci_upper"],
        "alternative": ["analysis.continuous_data.exposed_mean", "analysis.continuous_data.exposed_sd",
                        "analysis.continuous_data.exposed_n", "analysis.continuous_data.control_mean",
                        "analysis.continuous_data.control_sd", "analysis.continuous_data.control_n"],
        "fields": ["analysis.effect_value", "analysis.ci_lower", "analysis.ci_upper",
                   "analysis.continuous_data.exposed_mean", "analysis.continuous_data.exposed_sd",
                   "analysis.continuous_data.exposed_n", "analysis.continuous_data.control_mean",
                   "analysis.continuous_data.control_sd", "analysis.continuous_data.control_n"],
    },
    "SMD": {
        "primary": ["analysis.effect_value", "analysis.ci_lower", "analysis.ci_upper"],
        "alternative": ["analysis.continuous_data.exposed_mean", "analysis.continuous_data.exposed_sd",
                        "analysis.continuous_data.exposed_n", "analysis.continuous_data.control_mean",
                        "analysis.continuous_data.control_sd", "analysis.continuous_data.control_n"],
        "fields": ["analysis.effect_value", "analysis.ci_lower", "analysis.ci_upper",
                   "analysis.continuous_data.exposed_mean", "analysis.continuous_data.exposed_sd",
                   "analysis.continuous_data.exposed_n", "analysis.continuous_data.control_mean",
                   "analysis.continuous_data.control_sd", "analysis.continuous_data.control_n"],
    },
    "HR": {
        "primary": ["analysis.effect_value", "analysis.ci_lower", "analysis.ci_upper"],
        "alternative": ["analysis.survival_data.events_exposed", "analysis.survival_data.events_control",
                        "analysis.survival_data.person_time_exposed", "analysis.survival_data.person_time_control"],
        "fields": ["analysis.effect_value", "analysis.ci_lower", "analysis.ci_upper",
                   "analysis.survival_data.events_exposed", "analysis.survival_data.events_control",
                   "analysis.survival_data.person_time_exposed", "analysis.survival_data.person_time_control",
                   "analysis.survival_data.rate_exposed", "analysis.survival_data.rate_control"],
    },
}


class ValidationService:
    """Validate extractions and compute quality metrics"""

    @staticmethod
    def compute_quality_metrics(
        extracted_data: Dict[str, Any],
        raw_text: str
    ) -> ExtractionQuality:
        """
        Compute quality metrics for an extraction

        Considers:
        - Presence of required fields
        - Data quality
        - Parseability
        """
        missing_fields = []
        validation_warnings = []

        # Check required fields
        required_fields = {
            "metadata.title": "Study title",
            "methods.study_design": "Study design",
            "methods.sample_size": "Sample size",
            "analysis.exposure": "Exposure",
            "analysis.outcome": "Outcome",
            "analysis.effect_measure": "Effect measure",
        }

        def get_nested(data: Dict, path: str):
            """Get nested dict value by dot notation"""
            keys = path.split(".")
            val = data
            for key in keys:
                if isinstance(val, dict):
                    val = val.get(key)
                else:
                    return None
            return val

        # Check for missing fields
        for field_path, field_name in required_fields.items():
            if not get_nested(extracted_data, field_path):
                missing_fields.append(field_name)

        # Effect-size-specific validation
        effect_measure = get_nested(extracted_data, "analysis.effect_measure")
        if effect_measure:
            effect_measure = effect_measure.upper()
            effect_config = EFFECT_REQUIRED_FIELDS.get(effect_measure)
            if effect_config:
                # Check if primary fields are present
                primary_present = any(
                    get_nested(extracted_data, field) is not None
                    for field in effect_config["primary"]
                )
                # Check if alternative fields are present
                alternative_present = any(
                    get_nested(extracted_data, field) is not None
                    for field in effect_config["alternative"]
                )

                if not primary_present and not alternative_present:
                    missing_fields.append(
                        f"Effect-size-specific data for {effect_measure}"
                    )
                    validation_warnings.append(
                        f"Missing primary fields ({', '.join(effect_config['primary'])}) "
                        f"and alternative fields ({', '.join(effect_config['alternative'])})"
                    )
                elif not primary_present and alternative_present:
                    validation_warnings.append(
                        f"Primary effect estimate missing for {effect_measure}, "
                        f"but alternative data ({', '.join(effect_config['alternative'])}) is present"
                    )

        # Check for confidence indicators
        has_ci_bounds = (
            get_nested(extracted_data, "analysis.ci_lower") is not None and
            get_nested(extracted_data, "analysis.ci_upper") is not None
        )

        has_sample_size = get_nested(extracted_data, "methods.sample_size") is not None
        has_effect_value = get_nested(extracted_data, "analysis.effect_value") is not None

        # Check data quality
        sample_size = get_nested(extracted_data, "methods.sample_size")
        if sample_size and not isinstance(sample_size, int):
            validation_warnings.append("Sample size is not numeric")

        effect_value = get_nested(extracted_data, "analysis.effect_value")
        if effect_value and not isinstance(effect_value, (int, float)):
            validation_warnings.append("Effect value is not numeric")

        # Check CI bounds are in correct order
        ci_lower = get_nested(extracted_data, "analysis.ci_lower")
        ci_upper = get_nested(extracted_data, "analysis.ci_upper")
        if ci_lower and ci_upper and ci_lower > ci_upper:
            validation_warnings.append("CI lower bound > upper bound")

        # Check year is reasonable
        year = get_nested(extracted_data, "metadata.year")
        if year and (year < 1900 or year > 2100):
            validation_warnings.append("Year appears invalid")

        # Check proportion bounds
        proportion = get_nested(extracted_data, "analysis.proportion_data.proportion")
        if proportion is not None and (proportion < 0 or proportion > 1):
            validation_warnings.append("Proportion must be between 0 and 1")

        # Check 2×2 table cells are non-negative
        for cell in ["a", "b", "c", "d"]:
            cell_val = get_nested(extracted_data, f"analysis.two_by_two_table.{cell}")
            if cell_val is not None and cell_val < 0:
                validation_warnings.append(f"2×2 table cell '{cell}' is negative")

        # Calculate parseable score (0-1)
        # Based on presence of numeric effect estimates
        parseable_score = 0.0
        if has_effect_value:
            parseable_score += 0.4
        if has_ci_bounds:
            parseable_score += 0.3
        if has_sample_size:
            parseable_score += 0.3

        # Calculate overall confidence
        max_missing = 7  # Total required fields
        penalty_per_missing = 0.1
        missing_penalty = len(missing_fields) * penalty_per_missing
        warning_penalty = len(validation_warnings) * 0.05

        confidence_score = max(0, 1.0 - missing_penalty - warning_penalty)

        return ExtractionQuality(
            confidence_score=round(confidence_score, 2),
            missing_fields=missing_fields,
            validation_warnings=validation_warnings,
            has_ci_bounds=has_ci_bounds,
            has_sample_size=has_sample_size,
            has_effect_value=has_effect_value,
            parseable_score=round(parseable_score, 2)
        )

    @staticmethod
    def validate_extraction(study: ExtractedStudy) -> Tuple[bool, List[str]]:
        """
        Validate an extraction against schema

        Returns: (is_valid, errors)
        """
        errors = []

        # Check required fields exist
        if not study.metadata.title:
            errors.append("Missing study title")

        if not study.methods.study_design:
            errors.append("Missing study design")

        if not study.analysis.outcome:
            errors.append("Missing outcome")

        if not study.analysis.exposure:
            errors.append("Missing exposure")

        # Check data types
        if study.methods.sample_size and not isinstance(study.methods.sample_size, int):
            errors.append("Sample size must be integer")

        if study.analysis.effect_value and not isinstance(study.analysis.effect_value, (int, float)):
            errors.append("Effect value must be numeric")

        # Check effect measure matches specified type
        if study.analysis.effect_measure != study.effect_type:
            errors.append(
                f"Effect measure {study.analysis.effect_measure} doesn't match type {study.effect_type}"
            )

        # Check CI bounds
        if study.analysis.ci_lower and study.analysis.ci_upper:
            if study.analysis.ci_lower >= study.analysis.ci_upper:
                errors.append("CI lower bound must be less than upper bound")

        # Effect-size-specific validation
        effect_type = study.effect_type.value if study.effect_type else None
        if effect_type and effect_type in EFFECT_REQUIRED_FIELDS:
            effect_config = EFFECT_REQUIRED_FIELDS[effect_type]
            analysis_data = study.analysis.dict() if study.analysis else {}

            def get_nested(data, path):
                keys = path.split(".")
                val = data
                for key in keys:
                    if isinstance(val, dict):
                        val = val.get(key)
                    else:
                        return None
                return val

            primary_present = any(
                get_nested(analysis_data, field) is not None
                for field in effect_config["primary"]
            )
            alternative_present = any(
                get_nested(analysis_data, field) is not None
                for field in effect_config["alternative"]
            )

            if not primary_present and not alternative_present:
                errors.append(
                    f"Missing effect-size-specific data for {effect_type}. "
                    f"Need either ({', '.join(effect_config['primary'])}) "
                    f"or ({', '.join(effect_config['alternative'])})"
                )

        return len(errors) == 0, errors

    @staticmethod
    def should_retry(
        study: ExtractedStudy,
        max_attempts: int = 3
    ) -> bool:
        """Determine if extraction should be retried"""
        # Don't retry if too many attempts already
        if study.extraction_attempts >= max_attempts:
            return False

        # Retry if confidence is very low
        if study.confidence and study.confidence < 0.3:
            return True

        # Retry if quality metrics show critical issues
        if study.quality_metrics:
            # Retry if missing critical fields (title, outcome, exposure)
            # NOTE: Effect value is NOT required - studies can be accepted without effect sizes
            critical_fields = ["Study title", "Outcome", "Exposure"]
            for field in critical_fields:
                if field in study.quality_metrics.missing_fields:
                    return True

            # Retry if missing effect-size-specific data
            for field in study.quality_metrics.missing_fields:
                if "Effect-size-specific data" in field:
                    return True

        return False

class FileHashService:
    """Generate and manage file hashes for duplicate detection"""
    
    @staticmethod
    def compute_hash(file_contents: bytes) -> str:
        """Compute SHA256 hash of file"""
        return hashlib.sha256(file_contents).hexdigest()
    
    @staticmethod
    def compute_text_hash(text: str) -> str:
        """Compute hash of extracted text (more lenient for PDFs)"""
        # Normalize whitespace
        normalized = " ".join(text.split())
        return hashlib.sha256(normalized.encode()).hexdigest()

class ConsistencyService:
    """Ensure consistent extraction results"""
    
    @staticmethod
    def compare_extractions(
        extraction1: Dict[str, Any],
        extraction2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare two extractions for consistency
        
        Returns:
        {
            "similarity": 0-1,
            "identical_fields": [...],
            "different_fields": {...}
        }
        """
        different = {}
        identical = []
        
        # Compare key fields
        fields_to_compare = [
            ("metadata.title", "title"),
            ("metadata.year", "year"),
            ("methods.study_design", "design"),
            ("methods.sample_size", "n"),
            ("analysis.effect_measure", "effect"),
            ("analysis.effect_value", "value"),
        ]
        
        def get_nested(data: Dict, path: str):
            keys = path.split(".")
            val = data
            for key in keys:
                if isinstance(val, dict):
                    val = val.get(key)
                else:
                    return None
            return val
        
        for path, label in fields_to_compare:
            val1 = get_nested(extraction1, path)
            val2 = get_nested(extraction2, path)
            
            if val1 == val2:
                identical.append(label)
            else:
                different[label] = {"extraction1": val1, "extraction2": val2}
        
        # Calculate similarity
        total = len(fields_to_compare)
        similarity = len(identical) / total if total > 0 else 0
        
        return {
            "similarity": round(similarity, 2),
            "identical_fields": identical,
            "different_fields": different,
            "identical_count": len(identical),
            "different_count": len(different)
        }

# Global instances
validation_service = ValidationService()
file_hash_service = FileHashService()
consistency_service = ConsistencyService()

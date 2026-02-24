from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
import uuid

class EffectMeasure(str, Enum):
    OR = "OR"
    RR = "RR"
    HR = "HR"
    MD = "MD"
    SMD = "SMD"

class ExtractionQuality(BaseModel):
    """Quality metrics for extraction"""
    confidence_score: float = Field(..., ge=0, le=1, description="Overall confidence 0-1")
    missing_fields: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    has_ci_bounds: bool = False
    has_sample_size: bool = False
    has_effect_value: bool = False
    parseable_score: float = Field(..., ge=0, le=1)

class GroupStatistics(BaseModel):
    mean: Optional[float] = None
    sd: Optional[float] = None
    n: Optional[int] = None

class GroupData(BaseModel):
    exposed: Optional[GroupStatistics] = None
    control: Optional[GroupStatistics] = None

class Analysis(BaseModel):
    exposure: Optional[str] = None
    outcome: Optional[str] = None
    effect_measure: Optional[EffectMeasure] = None
    effect_value: Optional[float] = None
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    group_statistics: Optional[GroupData] = None

class Methods(BaseModel):
    study_design: Optional[str] = None
    population: Optional[str] = None
    sample_size: Optional[int] = None

class Metadata(BaseModel):
    study_id: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[str] = None
    year: Optional[int] = None
    journal: Optional[str] = None

class ExtractedStudy(BaseModel):
    filename: str
    effect_type: EffectMeasure
    metadata: Metadata
    methods: Methods
    analysis: Analysis
    meta_analysis_id: Optional[str] = None  # Reference to parent meta-analysis
    owner_id: Optional[str] = None
    raw_text: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    embedding: Optional[List[float]] = None
    quality_metrics: Optional[ExtractionQuality] = None
    file_hash: Optional[str] = None  # For duplicate detection
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: Optional[float] = None
    confidence: Optional[float] = None
    extraction_attempts: int = 1
    last_extraction_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "filename": "study_2024.pdf",
                "effect_type": "OR",
                "metadata": {
                    "title": "A study on disease X",
                    "authors": "John Doe, Jane Smith",
                    "year": 2024,
                    "journal": "Nature Medicine"
                },
                "methods": {
                    "study_design": "Case-control",
                    "population": "Adults aged 18-65",
                    "sample_size": 500
                },
                "analysis": {
                    "exposure": "Exposure to factor X",
                    "outcome": "Disease Y",
                    "effect_measure": "OR",
                    "effect_value": 2.5,
                    "ci_lower": 1.8,
                    "ci_upper": 3.2
                }
            }
        }

# Meta-Analysis Project Models
class MetaAnalysis(BaseModel):
    """Meta-analysis project grouping multiple studies"""
    meta_analysis_id: str = Field(description="Unique identifier for meta-analysis")
    title: str = Field(description="Title of the meta-analysis")
    details: Optional[str] = Field(None, description="Optional details/notes about the meta-analysis")
    outcome: Optional[str] = Field(None, description="Outcome variable for this meta-analysis")
    exposure: Optional[str] = Field(None, description="Exposure variable for this meta-analysis")
    owner_id: Optional[str] = Field(None, description="User ID who owns this meta-analysis")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    study_count: int = Field(default=0, description="Number of studies in this meta-analysis")
    studies: List[str] = Field(default_factory=list, description="List of study IDs")
    
    class Config:
        json_schema_extra = {
            "example": {
                "meta_analysis_id": "ma_2024_cardio_risk",
                "title": "Cardiovascular Risk Factors in Type 2 Diabetes",
                "details": "Systematic review of 25 studies on CV risk in T2DM patients",
                "created_at": "2024-01-15T10:30:00",
                "updated_at": "2024-01-15T10:30:00",
                "study_count": 25,
                "studies": ["study_1", "study_2", "..."]
            }
        }

# Batch Job Models
class BatchJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"  # Some succeeded, some failed

class BatchJobFile(BaseModel):
    """Individual file in batch"""
    filename: str
    status: str = "pending"  # pending, processing, success, failed
    study_id: Optional[str] = None
    error: Optional[str] = None
    processed_at: Optional[datetime] = None

class BatchJob(BaseModel):
    """Batch processing job"""
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    effect_type: EffectMeasure
    owner_id: Optional[str] = None
    meta_analysis_id: Optional[str] = None
    files: List[BatchJobFile] = Field(default_factory=list)
    status: BatchJobStatus = BatchJobStatus.PENDING
    total_files: int = 0
    processed_count: int = 0
    success_count: int = 0
    failed_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "batch_id": "batch_abc123",
                "effect_type": "OR",
                "files": [
                    {"filename": "study1.pdf", "status": "success", "study_id": "123"},
                    {"filename": "study2.pdf", "status": "processing"},
                    {"filename": "study3.pdf", "status": "pending"}
                ],
                "status": "processing",
                "total_files": 3,
                "processed_count": 1,
                "success_count": 1,
                "failed_count": 0
            }
        }

class StudyComparison(BaseModel):
    """Comparison between two studies"""
    study1_id: str
    study2_id: str
    study1_filename: str
    study2_filename: str
    similarity_score: float = Field(..., ge=0, le=1)
    differences: Dict[str, Any]
    similarities: Dict[str, Any]
    potential_duplicates: bool

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import time

from backend.models.schemas import (
    BatchJob, BatchJobFile, BatchJobStatus, ExtractedStudy,
    EffectMeasure, Metadata, Methods, Analysis
)
from backend.ingestion.pdf_parser import extract_text_from_pdf, parse_pdf
from backend.services.extraction import llm_extraction_service
from backend.services.embeddings import embedding_service
from backend.services.validation import (
    validation_service, file_hash_service, consistency_service
)
from backend.db.mongodb import insert_study, search_studies, update_study, add_study_to_meta_analysis, update_batch_job
from backend.db.vector_store import vector_store
from backend.config import settings

class BatchProcessingService:
    """Handle batch processing of multiple PDFs"""
    
    def __init__(self):
        self.active_jobs: Dict[str, BatchJob] = {}
        self.current_file: Dict[str, Optional[str]] = {}  # Track currently processing file per batch
    
    async def create_batch_job(
        self,
        files: List[tuple],  # List of (filename, file_contents)
        effect_type: EffectMeasure,
        owner_id: Optional[str] = None,
        meta_analysis_id: Optional[str] = None
    ) -> BatchJob:
        """Create a new batch job and initialize it"""
        batch_job = BatchJob(
            effect_type=effect_type,
            owner_id=owner_id,
            meta_analysis_id=meta_analysis_id,
            total_files=len(files),
            files=[BatchJobFile(filename=filename) for filename, _ in files]
        )
        
        self.active_jobs[batch_job.batch_id] = batch_job
        return batch_job
    
    async def process_batch(
        self,
        batch_job: BatchJob,
        files: List[tuple],  # List of (filename, file_contents)
        check_duplicates: bool = True,
        max_concurrent: int = 2
    ) -> BatchJob:
        """
        Process all files in batch
        
        Args:
            batch_job: Batch job to process
            files: List of (filename, file_contents)
            check_duplicates: Check for duplicate files
            max_concurrent: Max concurrent processing tasks
        """
        batch_job.status = BatchJobStatus.PROCESSING
        batch_job.started_at = datetime.utcnow()
        
        # Estimate time for 2 min per file
        batch_job.estimated_completion = batch_job.started_at + timedelta(
            minutes=2 * batch_job.total_files // max_concurrent
        )
        
        try:
            # Create processing tasks with concurrency limit
            semaphore = asyncio.Semaphore(max_concurrent)
            tasks = []
            
            for i, (filename, contents) in enumerate(files):
                task = self._process_single_file(
                    batch_job, i, filename, contents, check_duplicates, semaphore
                )
                tasks.append(task)
            
            # Process all tasks
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update batch status
            batch_job.completed_at = datetime.utcnow()
            
            if batch_job.failed_count == 0:
                batch_job.status = BatchJobStatus.COMPLETED
            elif batch_job.success_count == 0:
                batch_job.status = BatchJobStatus.FAILED
            else:
                batch_job.status = BatchJobStatus.PARTIAL
            
            # Save final state to database
            await update_batch_job(batch_job.batch_id, batch_job.dict())
        
        except Exception as e:
            batch_job.status = BatchJobStatus.FAILED
            print(f"Batch processing error: {e}")
            # Save failed state to database
            try:
                await update_batch_job(batch_job.batch_id, batch_job.dict())
            except:
                pass
        
        finally:
            # Clean up tracking
            if batch_job.batch_id in self.current_file:
                del self.current_file[batch_job.batch_id]
        
        return batch_job
    
    async def _process_single_file(
        self,
        batch_job: BatchJob,
        file_index: int,
        filename: str,
        file_contents: bytes,
        check_duplicates: bool,
        semaphore: asyncio.Semaphore
    ) -> None:
        """Process a single file in the batch"""
        async with semaphore:
            try:
                # Update file status
                file_record = batch_job.files[file_index]
                file_record.status = "processing"
                
                # Track current file being processed (for progress display)
                self.current_file[batch_job.batch_id] = filename
                
                # Check for duplicates if enabled
                if check_duplicates:
                    file_hash = file_hash_service.compute_hash(file_contents)
                    existing = await search_studies({"file_hash": file_hash}, owner_id=batch_job.owner_id)
                    
                    if existing:
                        file_record.status = "skipped"
                        file_record.study_id = str(existing[0]["_id"])
                        return
                else:
                    file_hash = None
                
                # Save temp file
                tmp_path = Path(settings.TEMP_DIR) / filename
                tmp_path.parent.mkdir(parents=True, exist_ok=True)
                with open(tmp_path, "wb") as f:
                    f.write(file_contents)
                
                # Extract text using GROBID (with PyPDF fallback)
                start_time = time.time()
                grobid_doc, used_grobid = await parse_pdf(tmp_path)
                full_text = grobid_doc.to_plain_text()

                # Pre-populate metadata from GROBID if available
                pre_filled_metadata: Dict[str, Any] = {}
                if used_grobid and grobid_doc.title:
                    pre_filled_metadata["title"] = grobid_doc.title
                if used_grobid and grobid_doc.publication_date:
                    try:
                        pre_filled_metadata["year"] = int(grobid_doc.publication_date[:4])
                    except (ValueError, TypeError):
                        pass
                if used_grobid and grobid_doc.authors:
                    pre_filled_metadata["authors"] = ", ".join(
                        a.raw_name for a in grobid_doc.authors if a.raw_name
                    )
                if used_grobid and grobid_doc.journal:
                    pre_filled_metadata["journal"] = grobid_doc.journal
                if used_grobid and grobid_doc.doi:
                    pre_filled_metadata["study_id"] = grobid_doc.doi
                
                # Extract structured data with semantic retrieval
                extracted_data = await llm_extraction_service.extract_study_data(
                    full_text,
                    batch_job.effect_type,
                    use_semantic_search=True,
                    pre_filled_metadata=pre_filled_metadata if pre_filled_metadata else None,
                )
                
                # Extract first author for progress display
                first_author = extracted_data.get("metadata", {}).get("authors", "Unknown")
                if first_author:
                    # Get just the first author name
                    first_author = first_author.split(",")[0].split(";")[0].split("and")[0].strip()
                else:
                    first_author = "Unknown"
                
                # Update current file with author info
                self.current_file[batch_job.batch_id] = f"{first_author} ({filename})"
                
                # Generate embedding
                try:
                    embedding = embedding_service.embed_study_text(full_text)
                except Exception as e:
                    embedding = None
                    print(f"Embedding error for {filename}: {e}")
                
                # Compute quality metrics
                quality_metrics = validation_service.compute_quality_metrics(
                    extracted_data,
                    full_text
                )
                
                # Build GROBID metadata dict for storage
                grobid_metadata = None
                if used_grobid:
                    grobid_metadata = grobid_doc.to_dict()

                # Create study document
                study = ExtractedStudy(
                    filename=filename,
                    effect_type=batch_job.effect_type,
                    metadata=Metadata(**extracted_data.get("metadata", {})),
                    methods=Methods(**extracted_data.get("methods", {})),
                    analysis=Analysis(**extracted_data.get("analysis", {})),
                    meta_analysis_id=batch_job.meta_analysis_id,
                    owner_id=batch_job.owner_id,
                    raw_text=full_text[:5000],
                    extracted_data=extracted_data,
                    embedding=embedding,
                    quality_metrics=quality_metrics,
                    file_hash=file_hash,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    confidence=quality_metrics.confidence_score,
                    grobid_metadata=grobid_metadata,
                    used_grobid=used_grobid,
                )
                
                # Save to MongoDB
                study_id = await insert_study(study)

                if batch_job.meta_analysis_id:
                    try:
                        await add_study_to_meta_analysis(
                            batch_job.meta_analysis_id,
                            study_id,
                            owner_id=batch_job.owner_id
                        )
                    except Exception as e:
                        print(f"Warning: Could not add study to meta-analysis: {e}")
                
                # Add to vector store
                if embedding:
                    await vector_store.add_vector(
                        study_id,
                        full_text,
                        embedding,
                        {
                            "filename": filename,
                            "effect_type": batch_job.effect_type.value,
                            "title": study.metadata.title,
                            "year": study.metadata.year,
                            "owner_id": batch_job.owner_id,
                            "quality_score": quality_metrics.confidence_score
                        }
                    )
                
                # Update file and batch status
                file_record.status = "success"
                file_record.study_id = study_id
                batch_job.success_count += 1
                
            except Exception as e:
                file_record.status = "failed"
                file_record.error = str(e)
                batch_job.failed_count += 1
                print(f"Error processing {filename}: {e}")
            
            finally:
                batch_job.processed_count += 1
                file_record.processed_at = datetime.utcnow()
                
                # Persist progress to database after each file
                try:
                    await update_batch_job(batch_job.batch_id, batch_job.dict())
                except Exception as e:
                    print(f"Warning: Could not save batch progress to database: {e}")
                
                # Clean up temp file
                try:
                    tmp_path = Path(settings.TEMP_DIR) / filename
                    if tmp_path.exists():
                        tmp_path.unlink()
                except:
                    pass
    
    def get_batch_status(self, batch_id: str) -> Optional[BatchJob]:
        """Get status of a batch job"""
        return self.active_jobs.get(batch_id)
    
    def list_active_batches(self) -> List[BatchJob]:
        """List all active batch jobs"""
        return list(self.active_jobs.values())

class RetryService:
    """Handle retrying failed or low-confidence extractions"""
    
    async def retry_low_confidence_studies(
        self,
        effect_type: str,
        confidence_threshold: float = 0.5,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Find and retry studies with low confidence
        
        Returns:
        {
            "total_checked": int,
            "retried": int,
            "improved": int,
            "still_low": int
        }
        """
        studies = await search_studies({
            "effect_type": effect_type,
            "confidence": {"$lt": confidence_threshold},
            "extraction_attempts": {"$lt": max_retries}
        })
        
        results = {
            "total_checked": len(studies),
            "retried": 0,
            "improved": 0,
            "still_low": 0
        }
        
        for study_doc in studies:
            try:
                # Retry extraction with semantic search
                extracted_data = await llm_extraction_service.extract_study_data(
                    study_doc.get("raw_text", ""),
                    EffectMeasure(study_doc["effect_type"]),
                    use_semantic_search=True
                )
                
                # Recompute quality metrics
                quality_metrics = validation_service.compute_quality_metrics(
                    extracted_data,
                    study_doc.get("raw_text", "")
                )
                
                new_confidence = quality_metrics.confidence_score
                old_confidence = study_doc.get("confidence", 0)
                
                # Update study
                await update_study(
                    str(study_doc["_id"]),
                    {
                        "confidence": new_confidence,
                        "quality_metrics": quality_metrics.dict(),
                        "extracted_data": extracted_data,
                        "extraction_attempts": study_doc.get("extraction_attempts", 1) + 1,
                        "last_extraction_at": datetime.utcnow()
                    }
                )
                
                results["retried"] += 1
                if new_confidence > old_confidence:
                    results["improved"] += 1
                else:
                    results["still_low"] += 1
            
            except Exception as e:
                print(f"Error retrying study {study_doc['filename']}: {e}")
        
        return results

# Global instances
batch_service = BatchProcessingService()
retry_service = RetryService()

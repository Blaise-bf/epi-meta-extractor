from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query, status, Depends, Request, Response, Body
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
import json
import os
import time
import jwt
from datetime import datetime
from typing import List, Any, Dict, Optional
from bson import ObjectId

from backend.config import settings
from backend.db.mongodb import (
    insert_study, get_study,
    get_studies_by_effect_type, get_all_studies, search_studies,
    save_batch_job, update_batch_job, get_batch_job, list_all_batch_jobs,
    update_study, get_batch_jobs_by_status, db_instance,
    create_meta_analysis, get_meta_analysis, get_studies_by_meta_analysis,
    list_all_meta_analyses, add_study_to_meta_analysis, delete_meta_analysis
)
from backend.db.vector_store import vector_store
from backend.ingestion.pdf_parser import extract_text_from_pdf, parse_pdf
from backend.services.grobid_client import GrobidExtractedDocument
from backend.services.extraction import llm_extraction_service
from backend.services.embeddings import embedding_service
from backend.services.validation import (
    validation_service, file_hash_service, consistency_service
)
from backend.services.batch import batch_service
from backend.services.csv_export import csv_export_service
from backend.services.auth import (
    create_access_token,
    decode_access_token,
    create_magic_link_token,
    verify_magic_link_token,
    get_or_create_user,
    get_user_by_id,
    create_refresh_token,
    revoke_refresh_token,
    get_user_from_refresh_token,
    send_magic_link
)
from backend.models.schemas import (
    ExtractedStudy, EffectMeasure, Metadata, Methods, Analysis,
    BatchJob, BatchJobStatus, MetaAnalysis
)

# Get MongoDB URI from environment
MONGODB_URI = os.environ.get("MONGODB_URI", settings.MONGODB_URI)
MONGODB_DB_NAME = os.environ.get("MONGODB_DB_NAME", settings.MONGODB_DB_NAME)
DEBUG = os.environ.get("DEBUG", "").strip().lower() in {"1", "true", "on", "yes"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle - startup and shutdown"""
    # Startup:
    client = AsyncIOMotorClient(
        MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000
    )
    database = client[MONGODB_DB_NAME]

    # Verify connection
    try:
        pong = await database.command("ping")
        if int(pong["ok"]) != 1:
            raise Exception("MongoDB connection is not okay!")
        print(f"✓ Connected to MongoDB: {MONGODB_DB_NAME}")
    except Exception as e:
        print(f"✗ Failed to connect to MongoDB: {e}")
        raise

    # Set database instance for global use
    db_instance.client = client
    db_instance.db = database

    # Initialize vector store
    try:
        await vector_store.init()
        print("✓ Initialized vector store")
    except Exception as e:
        print(f"⚠ Warning: Could not initialize vector store: {e}")

    print("✓ App startup complete")

    # Yield back to FastAPI
    yield

    # Shutdown:
    client.close()
    print("✓ App shutdown complete")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    description="API for extracting epidemiologic metadata from PDF studies",
    lifespan=lifespan,
    debug=DEBUG
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    print(f"[get_current_user] Credentials: {credentials}")
    print(f"[get_current_user] Has creds: {bool(credentials)}")
    if credentials:
        print(f"[get_current_user] Scheme: {credentials.scheme}")
        print(f"[get_current_user] Token start: {credentials.credentials[:20] if credentials.credentials else 'None'}...")

    if not credentials or credentials.scheme.lower() != "bearer":
        print(f"[get_current_user] 401: No credentials or wrong scheme")
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        print(f"[get_current_user] Decoded payload: {payload}")
    except jwt.ExpiredSignatureError as e:
        print(f"[get_current_user] 401: Token expired: {e}")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        print(f"[get_current_user] 401: Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"[get_current_user] 401: Token decode failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await get_user_by_id(payload.get("sub", ""))
    if not user:
        print(f"[get_current_user] 401: User not found for sub={payload.get('sub')}")
        raise HTTPException(status_code=401, detail="User not found")

    print(f"[get_current_user] Success: user_id={user.get('id')}")
    return user

# Create data directories
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.TEMP_DIR).mkdir(parents=True, exist_ok=True)

# Health check
@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME
    }


# GROBID health check
@app.get("/health/grobid")
async def grobid_health_check():
    """Check if GROBID service is available"""
    from backend.services.grobid_client import GrobidClient
    client = GrobidClient()
    try:
        available = await client.is_available()
        await client.close()
        return {
            "grobid_available": available,
            "grobid_url": settings.GROBID_URL,
            "grobid_enabled": settings.GROBID_ENABLED,
        }
    except Exception as e:
        await client.close()
        return {
            "grobid_available": False,
            "grobid_url": settings.GROBID_URL,
            "grobid_enabled": settings.GROBID_ENABLED,
            "error": str(e),
        }


def serialize_mongo_document(doc: Any) -> Any:
    """Convert MongoDB document to JSON-serializable format"""
    if doc is None:
        return None

    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            # Convert ObjectId to string
            if isinstance(value, ObjectId):
                result[key] = str(value)
            # Recursively serialize nested documents
            elif isinstance(value, dict):
                result[key] = serialize_mongo_document(value)
            elif isinstance(value, list):
                result[key] = [serialize_mongo_document(item) for item in value]
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    elif isinstance(doc, list):
        return [serialize_mongo_document(item) for item in doc]
    elif isinstance(doc, ObjectId):
        return str(doc)
    elif isinstance(doc, datetime):
        return doc.isoformat()
    else:
        return doc

# Schema endpoint
@app.get("/schema")
def get_schema(effect_type: str = Query(None)):
    """Get the expected extraction schema.

    If effect_type is provided, returns the effect-size-specific schema.
    Otherwise, returns the generic core schema.
    """
    from backend.schemas.loader import load_effect_schema, load_schema

    if effect_type:
        schema = load_effect_schema(effect_type)
        if schema:
            return schema
        raise HTTPException(
            status_code=400,
            detail=f"Invalid effect_type. Must be one of: {list_effect_schemas()}"
        )

    return load_schema()


# Auth endpoints
@app.post("/auth/request-link")
async def request_magic_link(
    email: str = Body(..., embed=True),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    token = await create_magic_link_token(email)
    background_tasks.add_task(send_magic_link, email, token)
    if DEBUG or not settings.SMTP_HOST:
        link = f"{settings.FRONTEND_ORIGIN}/auth?token={token}"
        return {"status": "sent", "magic_link": link}
    return {"status": "sent"}


@app.post("/auth/verify")
async def verify_magic_link(response: Response, token: str = Body(..., embed=True)):
    email = await verify_magic_link_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired link")

    user = await get_or_create_user(email)
    access_token = create_access_token(user["id"], user["email"])
    refresh_token = await create_refresh_token(user["id"])

    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )
    return {"access_token": access_token, "user": user}


@app.post("/auth/refresh")
async def refresh_access_token(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    user = await get_user_from_refresh_token(refresh_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = create_access_token(user["id"], user["email"])
    return {"access_token": access_token, "user": user}


@app.post("/auth/logout")
async def logout(request: Request, response: Response):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await revoke_refresh_token(refresh_token)
    response.delete_cookie("refresh_token")
    return {"status": "logged_out"}


@app.get("/auth/me")
async def auth_me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}

# Upload and process PDF
@app.post("/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    effect_type: Optional[str] = Query("OR"),
    meta_analysis_id: Optional[str] = Query(None),
    outcome: str = Query(...),
    exposure: Optional[str] = Query(None),
    population: Optional[str] = Query(None),
    comparison: Optional[str] = Query(None),
    study_design: Optional[str] = Query(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload and process a PDF or ZIP file

    Args:
        file: PDF file or ZIP archive containing PDFs
        effect_type: Effect measure type (OR, RR, HR, MD, SMD, PROPORTION) - via query param
        meta_analysis_id: Optional meta-analysis ID to group studies - via query param
        outcome: The outcome variable of interest (required)
        exposure: The exposure variable of interest (optional)
        population: Target population (optional)
        comparison: Comparison or intervention (optional)
        study_design: Expected study design (optional)
    """
    import zipfile
    import tempfile
    from pathlib import PurePosixPath

    # DEBUG: Log parameters
    print(f"[UPLOAD] Received parameters: effect_type={effect_type}, meta_analysis_id={meta_analysis_id}, outcome={outcome}, exposure={exposure}")

    try:
        owner_id = current_user["id"]

        # Validate effect type (allow None, will default to OR)
        if effect_type and effect_type not in [e.value for e in EffectMeasure]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid effect_type. Must be one of: {[e.value for e in EffectMeasure]}"
            )

        # Default to OR if not provided
        effect_type = effect_type or "OR"

        if meta_analysis_id:
            meta_analysis = await get_meta_analysis(meta_analysis_id, owner_id=owner_id)
            if not meta_analysis:
                raise HTTPException(status_code=404, detail="Meta-analysis not found")

        # Save uploaded file to a temporary directory that will be cleaned up
        import tempfile
        import shutil
        temp_dir = Path(tempfile.mkdtemp(dir=settings.TEMP_DIR))
        tmp_path = temp_dir / file.filename

        contents = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(contents)

        def _safe_zip_name(name: str) -> str | None:
            normalized = name.replace("\\", "/")
            path = PurePosixPath(normalized)
            if path.is_absolute() or ".." in path.parts:
                return None
            if not normalized.strip() or normalized.endswith("/"):
                return None
            return normalized

        # Check if ZIP file
        if file.filename.lower().endswith('.zip'):
            # Extract PDFs from ZIP
            file_list = []
            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                for zip_info in zip_ref.filelist:
                    if zip_info.is_dir():
                        continue
                    safe_name = _safe_zip_name(zip_info.filename)
                    if not safe_name:
                        continue
                    if safe_name.lower().endswith('.pdf'):
                        pdf_contents = zip_ref.read(zip_info.filename)
                        file_list.append((safe_name, pdf_contents))

            if not file_list:
                raise HTTPException(
                    status_code=400,
                    detail="No PDF files found in the ZIP archive"
                )

            if meta_analysis_id:
                meta_analysis = await get_meta_analysis(meta_analysis_id, owner_id=owner_id)
                if not meta_analysis:
                    raise HTTPException(status_code=404, detail="Meta-analysis not found")

            # Create batch job
            batch_job = await batch_service.create_batch_job(
                file_list,
                EffectMeasure(effect_type),
                owner_id=owner_id,
                meta_analysis_id=meta_analysis_id,
                outcome=outcome,
                exposure=exposure,
                population=population,
                comparison=comparison,
                study_design=study_design
            )

            # Save initial batch job
            await save_batch_job(batch_job)

            # Start processing in background
            import asyncio
            asyncio.create_task(
                batch_service.process_batch(
                    batch_job,
                    file_list,
                    check_duplicates=True
                )
            )

            # Clean up the uploaded ZIP file immediately since PDFs are now in memory
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

            return {
                "status": "batch_created",
                "batch_id": batch_job.batch_id,
                "num_files": len(file_list),
                "effect_type": effect_type,
                "message": f"Batch processing started for {len(file_list)} PDF files"
            }

        # Handle single PDF — use unified parser (Marker → GROBID → PyPDF)
        grobid_doc, used_grobid = await parse_pdf(tmp_path)
        full_text = grobid_doc.to_plain_text()

        # Get page count directly from the PDF
        from pypdf import PdfReader
        num_pages = len(PdfReader(str(tmp_path)).pages)

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

        # Extract structured data using LLM with semantic search
        extracted_data = await llm_extraction_service.extract_study_data(
            full_text,
            EffectMeasure(effect_type),
            outcome=outcome,
            exposure=exposure,
            population=population,
            comparison=comparison,
            study_design=study_design,
            use_semantic_search=True,
            pre_filled_metadata=pre_filled_metadata if pre_filled_metadata else None,
            use_rag_chains=settings.USE_RAG_CHAINS,
        )

        # Check if study is relevant (has outcome; exposure is optional)
        if not extracted_data or not extracted_data.get("analysis"):
            return {
                "status": "not_relevant",
                "message": f"Study is not relevant: No analysis data found related to outcome '{outcome}'",
                "extracted_data": extracted_data or {}
            }

        analysis = extracted_data.get("analysis", {})
        extracted_outcome = analysis.get("outcome", "")
        extracted_exposure = analysis.get("exposure", "")

        # Validate that extracted outcome matches what user requested
        # Exposure is optional, so only validate if provided
        if not extracted_outcome:
            return {
                "status": "not_relevant",
                "message": f"Study does not contain data about outcome '{outcome}'",
                "extracted_data": extracted_data
            }

        # Check for semantic match (normalized token overlap + fuzzy match)
        import re
        from difflib import SequenceMatcher

        def _normalize(text: str) -> str:
            normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
            return " ".join(normalized.split())

        def _token_set(text: str) -> set[str]:
            return {token for token in _normalize(text).split() if len(token) > 2}

        def _token_overlap(query: str, candidate: str) -> float:
            query_tokens = _token_set(query)
            if not query_tokens:
                return 0.0
            candidate_tokens = _token_set(candidate)
            return len(query_tokens & candidate_tokens) / len(query_tokens)

        def _fuzzy_ratio(a: str, b: str) -> float:
            return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()

        outcome_match = (
            _normalize(outcome) in _normalize(extracted_outcome)
            or _token_overlap(outcome, extracted_outcome) >= 0.5
            or _fuzzy_ratio(outcome, extracted_outcome) >= 0.72
        )

        # Only check exposure match if exposure was provided
        exposure_match = True
        if exposure:
            exposure_match = (
                _normalize(exposure) in _normalize(extracted_exposure)
                or _token_overlap(exposure, extracted_exposure) >= 0.5
                or _fuzzy_ratio(exposure, extracted_exposure) >= 0.72
            )

        if not (outcome_match and exposure_match):
            return {
                "status": "not_relevant",
                "message": f"Study relevance mismatch. Requested: '{exposure}' → '{outcome}'. Found: '{extracted_exposure}' → '{extracted_outcome}'",
                "extracted_data": extracted_data
            }

        # Generate embedding
        try:
            embedding = embedding_service.embed_study_text(full_text)
        except Exception as e:
            print(f"Warning: Could not generate embedding: {e}")
            embedding = None

        start_time = time.time()
        processing_time = (time.time() - start_time) * 1000  # Convert to ms

        # Create study document with extracted data
        # Extract nested objects from the extraction result, providing empty dicts as defaults
        metadata_dict = extracted_data.get("metadata") or {}
        methods_dict = extracted_data.get("methods") or {}
        analysis_dict = extracted_data.get("analysis") or {}

        # Build GROBID metadata dict for storage
        grobid_metadata = None
        if used_grobid:
            grobid_metadata = grobid_doc.to_dict()

        study = ExtractedStudy(
            filename=file.filename,
            effect_type=EffectMeasure(effect_type),
            metadata=Metadata(**metadata_dict),
            methods=Methods(**methods_dict),
            analysis=Analysis(**analysis_dict),
            meta_analysis_id=meta_analysis_id,
            owner_id=owner_id,
            raw_text=full_text[:5000],  # Store first 5000 chars
            extracted_data=extracted_data,
            embedding=embedding,
            processing_time_ms=processing_time,
            grobid_metadata=grobid_metadata,
            used_grobid=used_grobid,
        )

        # Save to MongoDB
        study_id = await insert_study(study)

        # Add to meta-analysis if meta_analysis_id provided
        if meta_analysis_id:
            try:
                await add_study_to_meta_analysis(meta_analysis_id, study_id, owner_id=owner_id)
            except Exception as e:
                print(f"Warning: Could not add study to meta-analysis: {e}")

        # Add to vector store in background
        if embedding:
            background_tasks.add_task(
                vector_store.add_vector,
                study_id,
                full_text,
                embedding,
                {
                    "filename": file.filename,
                    "effect_type": effect_type,
                    "title": study.metadata.title if study.metadata else None,
                    "year": study.metadata.year if study.metadata else None,
                    "owner_id": owner_id
                }
            )

        # Clean up temporary file and directory after extraction
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

        return {
            "status": "success",
            "study_id": study_id,
            "file_name": file.filename,
            "effect_type": effect_type,
            "num_pages": num_pages,
            "processing_time_ms": processing_time,
            "extracted_data": extracted_data
        }

    except HTTPException:
        # Clean up on HTTP exceptions too
        try:
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"[UPLOAD ERROR] {error_msg}")
        # Clean up on general exceptions
        try:
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {error_msg}"
        )

# Get study by ID
@app.get("/studies/{study_id}")
async def get_study_endpoint(study_id: str, current_user: dict = Depends(get_current_user)):
    """Get a study by ID"""
    try:
        study = await get_study(study_id, owner_id=current_user["id"])
        if not study:
            raise HTTPException(status_code=404, detail="Study not found")
        # Convert ObjectId to string for JSON serialization
        study["_id"] = str(study["_id"])
        return study
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get studies by effect type
@app.get("/studies/effect/{effect_type}")
async def get_studies_by_effect(effect_type: str, current_user: dict = Depends(get_current_user)):
    """Get all studies for a specific effect type"""
    try:
        if effect_type not in [e.value for e in EffectMeasure]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid effect_type. Must be one of: {[e.value for e in EffectMeasure]}"
            )

        studies = await get_studies_by_effect_type(effect_type, owner_id=current_user["id"])
        # Convert ObjectIds to strings
        for study in studies:
            study["_id"] = str(study["_id"])

        return {
            "effect_type": effect_type,
            "count": len(studies),
            "studies": studies
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get all studies
@app.get("/studies")
async def get_all_studies_endpoint(current_user: dict = Depends(get_current_user)):
    """Get all studies"""
    try:
        studies = await get_all_studies(owner_id=current_user["id"])
        # Convert ObjectIds to strings
        for study in studies:
            study["_id"] = str(study["_id"])

        return {
            "total": len(studies),
            "studies": studies
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# CSV Export endpoint
@app.get("/studies/export/csv")
async def export_studies_csv(current_user: dict = Depends(get_current_user)):
    """Export all studies as CSV file"""
    try:
        studies = await get_all_studies(owner_id=current_user["id"])
        # Convert ObjectIds to strings
        for study in studies:
            study["_id"] = str(study["_id"])

        if not studies:
            return JSONResponse(
                status_code=204,
                content={"message": "No studies to export"}
            )

        csv_content = csv_export_service.export_to_csv_bytes(studies)

        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=epi_studies_export.csv"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Meta-Analysis Endpoints
@app.post("/meta-analyses")
async def create_meta_analysis_endpoint(
    title: str = Query(...),
    details: Optional[str] = Query(""),
    outcome: Optional[str] = Query(None),
    exposure: Optional[str] = Query(None),
    population: Optional[str] = Query(None),
    comparison: Optional[str] = Query(None),
    study_design: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Create a new meta-analysis project"""
    try:
        import hashlib
        # Generate meta-analysis ID from title (simplified slug)
        slug = title.lower().replace(" ", "_")[:20]
        timestamp = int(time.time() * 1000) % 10000
        meta_analysis_id = f"ma_{slug}_{timestamp}"

        meta_analysis = await create_meta_analysis(
            meta_analysis_id=meta_analysis_id,
            title=title,
            details=details if details else None,
            outcome=outcome,
            exposure=exposure,
            population=population,
            comparison=comparison,
            study_design=study_design,
            owner_id=current_user["id"]
        )

        return {
            "meta_analysis_id": meta_analysis_id,
            "title": title,
            "details": details,
            "outcome": outcome,
            "exposure": exposure,
            "population": population,
            "comparison": comparison,
            "study_design": study_design,
            "created_at": meta_analysis["created_at"].isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/meta-analyses/{meta_analysis_id}")
async def get_meta_analysis_endpoint(meta_analysis_id: str, current_user: dict = Depends(get_current_user)):
    """Get a meta-analysis by ID"""
    try:
        meta_analysis = await get_meta_analysis(meta_analysis_id, owner_id=current_user["id"])
        if not meta_analysis:
            raise HTTPException(status_code=404, detail="Meta-analysis not found")

        # Format datetime for JSON serialization
        meta_analysis["created_at"] = meta_analysis["created_at"].isoformat()
        meta_analysis["updated_at"] = meta_analysis["updated_at"].isoformat()

        return meta_analysis
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/meta-analyses/{meta_analysis_id}/studies")
async def get_meta_analysis_studies_endpoint(meta_analysis_id: str, current_user: dict = Depends(get_current_user)):
    """Get all studies in a meta-analysis"""
    try:
        studies = await get_studies_by_meta_analysis(meta_analysis_id, owner_id=current_user["id"])

        return {
            "meta_analysis_id": meta_analysis_id,
            "total": len(studies),
            "studies": studies
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/meta-analyses")
async def list_meta_analyses_endpoint(current_user: dict = Depends(get_current_user)):
    """Get all meta-analyses"""
    try:
        print(f"[GET /meta-analyses] User: {current_user.get('id')}, Email: {current_user.get('email')}")

        meta_analyses = await list_all_meta_analyses(owner_id=current_user["id"])

        print(f"[GET /meta-analyses] Found {len(meta_analyses)} meta-analyses for user {current_user.get('id')}")

        # Format datetime for JSON serialization
        for ma in meta_analyses:
            ma["created_at"] = ma["created_at"].isoformat()
            ma["updated_at"] = ma["updated_at"].isoformat()

        return {
            "total": len(meta_analyses),
            "meta_analyses": meta_analyses
        }
    except Exception as e:
        print(f"[GET /meta-analyses] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/meta-analyses/{meta_analysis_id}")
async def delete_meta_analysis_endpoint(meta_analysis_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a meta-analysis and all associated studies"""
    print(f"[DELETE] Attempting to delete meta-analysis: {meta_analysis_id} for user: {current_user.get('id')}")
    try:
        # Verify meta-analysis exists first
        meta_analysis = await get_meta_analysis(meta_analysis_id, owner_id=current_user["id"])
        if not meta_analysis:
            print(f"[DELETE ERROR] Meta-analysis {meta_analysis_id} not found or user doesn't own it")
            raise HTTPException(status_code=404, detail="Meta-analysis not found or you don't have permission to delete it")

        # Delete the meta-analysis and all its studies
        success = await delete_meta_analysis(meta_analysis_id, owner_id=current_user["id"])

        if not success:
            print(f"[DELETE ERROR] Failed to delete meta-analysis {meta_analysis_id}")
            raise HTTPException(status_code=404, detail="Failed to delete meta-analysis")

        print(f"[DELETE SUCCESS] Meta-analysis {meta_analysis_id} deleted successfully")
        return {
            "status": "success",
            "message": f"Meta-analysis {meta_analysis_id} and all associated studies have been deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[DELETE EXCEPTION] Error deleting meta-analysis {meta_analysis_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# RAG/Semantic search
@app.post("/search")
async def semantic_search(
    query: str,
    limit: int = 5,
    score_threshold: float = 0.7,
    current_user: dict = Depends(get_current_user)
):
    """
    Semantic search across studies

    Args:
        query: Search query
        limit: Maximum number of results
        score_threshold: Minimum similarity score
    """
    try:
        # Get embedding for query
        query_embedding = embedding_service.get_embedding(query)

        # Search in vector store
        results = await vector_store.search(
            query_embedding,
            limit=limit,
            score_threshold=score_threshold
        )

        owner_id = current_user["id"]
        results = [result for result in results if result.get("metadata", {}).get("owner_id") == owner_id]

        return {
            "query": query,
            "results_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# BATCH PROCESSING ENDPOINTS
# =========================

@app.post("/batch/create")
async def create_batch(
    files: List[UploadFile] = File(...),
    effect_type: str = "OR",
    check_duplicates: bool = True
):
    """
    Create and start a batch processing job

    Args:
        files: List of PDF files to process
        effect_type: Effect measure type (OR, RR, HR, MD, SMD)
        check_duplicates: Check for duplicate files
    """
    try:
        # Validate effect type
        if effect_type not in [e.value for e in EffectMeasure]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid effect_type. Must be one of: {[e.value for e in EffectMeasure]}"
            )

        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        # Read file contents
        file_list = []
        for file in files:
            contents = await file.read()
            file_list.append((file.filename, contents))

        # Create batch job
        batch_job = await batch_service.create_batch_job(
            file_list,
            EffectMeasure(effect_type)
        )

        # Save initial batch job
        await save_batch_job(batch_job)

        # Start processing in background
        # Note: In production, use a task queue like Celery
        import asyncio
        asyncio.create_task(
            batch_service.process_batch(
                batch_job,
                file_list,
                check_duplicates=check_duplicates
            )
        )

        return {
            "status": "success",
            "batch_id": batch_job.batch_id,
            "total_files": batch_job.total_files,
            "effect_type": effect_type,
            "message": "Batch processing started"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str):
    """Get status of a batch job"""
    import time
    import asyncio
    start_time = time.time()

    try:
        # Use a timeout for the MongoDB query
        try:
            batch_job = await asyncio.wait_for(
                get_batch_job(batch_id),
                timeout=5.0  # 5 second timeout for MongoDB query
            )
        except asyncio.TimeoutError:
            print(f"[TIMEOUT] MongoDB query for batch {batch_id} timed out after 5s")
            raise HTTPException(
                status_code=504,
                detail="Database query timeout - batch processing may be overloaded"
            )

        db_time = time.time() - start_time

        if not batch_job:
            raise HTTPException(status_code=404, detail="Batch job not found")

        # Get currently processing file if available from in-memory cache
        current_file = batch_service.current_file.get(batch_id)

        # Serialize MongoDB document to JSON-safe format
        serialize_start = time.time()
        response = serialize_mongo_document(batch_job)
        serialize_time = time.time() - serialize_start

        # Add current file info
        response['current_file'] = current_file

        # Ensure all fields are present for consistency with frontend expectations
        response.setdefault('processed_count', 0)
        response.setdefault('total_files', 0)
        response.setdefault('status', 'pending')

        total_time = time.time() - start_time
        if total_time > 1.0:  # Log if taking more than 1 second
            print(f"[PERF] Batch status slow: total={total_time:.2f}s, db={db_time:.2f}s, serialize={serialize_time:.2f}s")

        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting batch status for {batch_id}: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/batch")
async def list_batches(
    status: str = Query(None, description="Filter by status"),
    limit: int = 50
):
    """List batch jobs"""
    try:
        if status:
            jobs = await get_batch_jobs_by_status(status)
        else:
            jobs = await list_all_batch_jobs(limit=limit)

        # Serialize all batch jobs for JSON response
        serialized_jobs = [serialize_mongo_document(job) for job in jobs]

        return {
            "total": len(serialized_jobs),
            "jobs": serialized_jobs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# QUALITY & VALIDATION ENDPOINTS
# =========================

@app.get("/studies/{study_id}/quality")
async def get_study_quality(study_id: str):
    """Get quality metrics for a study"""
    try:
        study = await get_study(study_id)
        if not study:
            raise HTTPException(status_code=404, detail="Study not found")

        return {
            "study_id": study_id,
            "filename": study.get("filename"),
            "confidence": study.get("confidence"),
            "quality_metrics": study.get("quality_metrics"),
            "extraction_attempts": study.get("extraction_attempts", 1)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/studies/{study_id}/retry")
async def retry_extraction(study_id: str):
    """Retry extraction for a study"""
    try:
        study_doc = await get_study(study_id)
        if not study_doc:
            raise HTTPException(status_code=404, detail="Study not found")

        # Check if should retry
        from backend.models.schemas import ExtractedStudy
        study = ExtractedStudy(**{k: v for k, v in study_doc.items() if k != "_id"})

        if not validation_service.should_retry(study):
            raise HTTPException(
                status_code=400,
                detail="Study does not meet retry criteria"
            )

        # Retry extraction with semantic search
        extracted_data = await llm_extraction_service.extract_study_data(
            study_doc.get("raw_text", ""),
            study.effect_type,
            use_semantic_search=True,
            use_rag_chains=settings.USE_RAG_CHAINS,
        )

        # Recompute quality metrics
        quality_metrics = validation_service.compute_quality_metrics(
            extracted_data,
            study_doc.get("raw_text", "")
        )

        # Update study
        await update_study(
            study_id,
            {
                "confidence": quality_metrics.confidence_score,
                "quality_metrics": quality_metrics.dict(),
                "extracted_data": extracted_data,
                "extraction_attempts": study_doc.get("extraction_attempts", 1) + 1,
                "last_extraction_at": datetime.utcnow()
            }
        )

        return {
            "status": "success",
            "study_id": study_id,
            "old_confidence": study.confidence,
            "new_confidence": quality_metrics.confidence_score,
            "quality_metrics": quality_metrics.dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/studies/retry-low-confidence")
async def retry_low_confidence(
    effect_type: str,
    confidence_threshold: float = 0.5
):
    """
    Retry all low-confidence extractions for an effect type

    Args:
        effect_type: Effect measure type to retry
        confidence_threshold: Only retry studies below this score
    """
    try:
        if effect_type not in [e.value for e in EffectMeasure]:
            raise HTTPException(status_code=400, detail="Invalid effect_type")

        results = await retry_service.retry_low_confidence_studies(
            effect_type,
            confidence_threshold
        )

        return {
            "status": "success",
            "effect_type": effect_type,
            "results": results
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# COMPARISON ENDPOINTS
# =========================

@app.get("/studies/{study_id1}/compare/{study_id2}")
async def compare_studies(study_id1: str, study_id2: str):
    """Compare two studies for consistency"""
    try:
        study1 = await get_study(study_id1)
        study2 = await get_study(study_id2)

        if not study1:
            raise HTTPException(status_code=404, detail=f"Study {study_id1} not found")
        if not study2:
            raise HTTPException(status_code=404, detail=f"Study {study_id2} not found")

        comparison = consistency_service.compare_extractions(
            study1.get("extracted_data", {}),
            study2.get("extracted_data", {})
        )

        return {
            "study_id1": study_id1,
            "study_id2": study_id2,
            "study1_filename": study1.get("filename"),
            "study2_filename": study2.get("filename"),
            "comparison": comparison
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/studies/effect/{effect_type}/compare")
async def compare_all_studies_in_effect(
    effect_type: str,
    limit: int = Query(5, description="Limit comparisons")
):
    """Compare all studies for consistency within an effect type"""
    try:
        if effect_type not in [e.value for e in EffectMeasure]:
            raise HTTPException(status_code=400, detail="Invalid effect_type")

        studies = await get_studies_by_effect_type(effect_type)

        if len(studies) < 2:
            return {
                "effect_type": effect_type,
                "message": "Need at least 2 studies to compare",
                "comparisons": []
            }

        # Compare first N studies pairwise
        comparisons = []
        for i in range(min(limit, len(studies))):
            for j in range(i + 1, min(limit, len(studies))):
                comp = consistency_service.compare_extractions(
                    studies[i].get("extracted_data", {}),
                    studies[j].get("extracted_data", {})
                )

                comparisons.append({
                    "study1": str(studies[i]["_id"]),
                    "study2": str(studies[j]["_id"]),
                    "study1_filename": studies[i].get("filename"),
                    "study2_filename": studies[j].get("filename"),
                    "similarity": comp["similarity"]
                })

        return {
            "effect_type": effect_type,
            "total_studies": len(studies),
            "comparison_count": len(comparisons),
            "comparisons": comparisons
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# RAG CHAT ENDPOINT
# =========================

from backend.services.rag import run_parallel_extraction, extract_with_agent

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    study_id: Optional[str] = None
    effect_type: Optional[str] = "OR"

@app.post("/chat")
async def chat_with_studies(request: ChatRequest):
    """Chat with the RAG system about uploaded studies.

    Follows the RealPython RAG chatbot pattern where a user can ask
    natural language questions about their studies.
    """
    try:
        # Get the last user message
        user_messages = [m for m in request.messages if m.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="No user message found")

        query = user_messages[-1].content

        # If study_id is provided, load that study's text
        study_text = ""
        if request.study_id:
            study = await get_study(request.study_id)
            if study:
                study_text = study.get("raw_text", "")
            else:
                raise HTTPException(status_code=404, detail="Study not found")
        else:
            # Load all studies for the user
            # For now, we'll use a placeholder
            study_text = "No specific study selected. Please provide a study_id."

        # Use the agent-based extraction for chat responses
        result = await extract_with_agent(
            study_text=study_text,
            effect_type=request.effect_type or "OR",
            query=query,
        )

        return {
            "response": result.get("output", "No response generated"),
            "intermediate_steps": result.get("intermediate_steps", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

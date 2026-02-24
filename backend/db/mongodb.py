from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError
from typing import List, Optional, Dict, Any
from datetime import datetime
from backend.config import settings
from backend.models.schemas import ExtractedStudy
from bson.objectid import ObjectId

class Database:
    client: AsyncIOMotorClient = None
    db: AsyncIOMotorDatabase = None

db_instance = Database()

async def connect_to_mongodb():
    """Connect to MongoDB"""
    import asyncio
    
    db_instance.client = AsyncIOMotorClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=10000,  # Prevent socket operations from hanging
        maxPoolSize=200,  # Increase connection pool for concurrent operations
        minPoolSize=10,  # Keep connections ready
        maxIdleTimeMS=30000,  # Close idle connections after 30s
        waitQueueTimeoutMS=5000,  # Max time to wait for available connection
    )
    db_instance.db = db_instance.client[settings.MONGODB_DB_NAME]
    
    # Verify connection by pinging
    try:
        await db_instance.db.command('ping')
        print(f"✓ Connected to MongoDB: {settings.MONGODB_DB_NAME}")
    except Exception as e:
        print(f"✗ Failed to connect to MongoDB: {e}")
        raise
    
    # Create indexes for studies
    try:
        try:
            await db_instance.db["studies"].drop_index("filename_1")
        except Exception:
            pass
        await db_instance.db["studies"].create_index(
            [("owner_id", 1), ("filename", 1)],
            unique=True
        )
        await db_instance.db["studies"].create_index("metadata.study_id")
        await db_instance.db["studies"].create_index("uploaded_at")
        await db_instance.db["studies"].create_index("file_hash")  # For duplicate detection
        await db_instance.db["studies"].create_index("confidence")  # For filtering
        await db_instance.db["studies"].create_index("effect_type")  # For filtering
        await db_instance.db["studies"].create_index("owner_id")
        
        # Create indexes for batch jobs
        await db_instance.db["batch_jobs"].create_index("batch_id", unique=True)
        await db_instance.db["batch_jobs"].create_index("status")
        await db_instance.db["batch_jobs"].create_index("created_at")
        await db_instance.db["batch_jobs"].create_index("owner_id")  # For user-specific queries

        # Users and auth tokens
        await db_instance.db["users"].create_index("email", unique=True)
        await db_instance.db["auth_tokens"].create_index("token_hash", unique=True)
        await db_instance.db["auth_tokens"].create_index("expires_at")
        await db_instance.db["refresh_tokens"].create_index("token_hash", unique=True)
        await db_instance.db["refresh_tokens"].create_index("expires_at")

        # Meta-analyses
        await db_instance.db["meta_analyses"].create_index("meta_analysis_id", unique=True)
        await db_instance.db["meta_analyses"].create_index("owner_id")
        
        print("✓ Created MongoDB indexes")
    except Exception as e:
        print(f"⚠ Warning: Could not create indexes: {e}")
        # Don't fail startup if indexes can't be created

async def close_mongodb():
    """Disconnect from MongoDB"""
    if db_instance.client:
        db_instance.client.close()
        print("✓ Disconnected from MongoDB")

async def insert_study(study: ExtractedStudy) -> str:
    """Insert an extracted study into MongoDB"""
    try:
        result = await db_instance.db["studies"].insert_one(
            study.model_dump()
        )
        return str(result.inserted_id)
    except DuplicateKeyError:
        # Update if already exists
        update_result = await db_instance.db["studies"].update_one(
            {"filename": study.filename, "owner_id": study.owner_id},
            {"$set": study.model_dump()}
        )
        return update_result.upserted_id or study.filename

async def get_study(study_id: str, owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a study by ID"""
    try:
        query = {"_id": ObjectId(study_id)}
        if owner_id:
            query["owner_id"] = owner_id
        return await db_instance.db["studies"].find_one(
            query
        )
    except:
        query = {"filename": study_id}
        if owner_id:
            query["owner_id"] = owner_id
        return await db_instance.db["studies"].find_one(query)

async def get_studies_by_effect_type(effect_type: str, owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all studies for a specific effect type"""
    query = {"effect_type": effect_type}
    if owner_id:
        query["owner_id"] = owner_id
    cursor = db_instance.db["studies"].find(query)
    return await cursor.to_list(length=None)

async def get_all_studies(owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all studies"""
    if db_instance.db is None:
        raise Exception("Database not initialized. Check MongoDB connection in app startup.")
    query: Dict[str, Any] = {}
    if owner_id:
        query["owner_id"] = owner_id
    cursor = db_instance.db["studies"].find(query)
    return await cursor.to_list(length=None)

async def update_study(study_id: str, update_data: Dict[str, Any]) -> bool:
    """Update a study"""
    try:
        result = await db_instance.db["studies"].update_one(
            {"_id": ObjectId(study_id)},
            {"$set": update_data}
        )
        return result.modified_count > 0
    except:
        return False

async def delete_study(study_id: str) -> bool:
    """Delete a study"""
    try:
        result = await db_instance.db["studies"].delete_one(
            {"_id": ObjectId(study_id)}
        )
        return result.deleted_count > 0
    except:
        return False

async def search_studies(query: Dict[str, Any], owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Search studies with flexible query"""
    if owner_id:
        query = {**query, "owner_id": owner_id}
    cursor = db_instance.db["studies"].find(query)
    return await cursor.to_list(length=None)

# Batch Job Operations
async def save_batch_job(batch_job: "BatchJob") -> str:
    """Save a batch job"""
    result = await db_instance.db["batch_jobs"].insert_one(
        batch_job.model_dump()
    )
    return str(result.inserted_id)

async def update_batch_job(batch_id: str, update_data: Dict[str, Any]) -> bool:
    """Update a batch job"""
    result = await db_instance.db["batch_jobs"].update_one(
        {"batch_id": batch_id},
        {"$set": update_data}
    )
    return result.modified_count > 0

async def get_batch_job(batch_id: str) -> Optional[Dict[str, Any]]:
    """Get a batch job by ID"""
    return await db_instance.db["batch_jobs"].find_one({"batch_id": batch_id})

async def get_batch_jobs_by_status(status: str) -> List[Dict[str, Any]]:
    """Get all batch jobs with a specific status"""
    cursor = db_instance.db["batch_jobs"].find({"status": status})
    return await cursor.to_list(length=None)

async def list_all_batch_jobs(limit: int = 50) -> List[Dict[str, Any]]:
    """List all batch jobs"""
    cursor = db_instance.db["batch_jobs"].find().sort("created_at", -1).limit(limit)
    return await cursor.to_list(length=limit)
# Meta-Analysis Functions
async def create_meta_analysis(meta_analysis_id: str, title: str, details: Optional[str] = None, outcome: Optional[str] = None, exposure: Optional[str] = None, owner_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new meta-analysis project"""
    meta_analysis = {
        "meta_analysis_id": meta_analysis_id,
        "title": title,
        "details": details,
        "outcome": outcome,
        "exposure": exposure,
        "owner_id": owner_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "study_count": 0,
        "studies": []
    }
    result = await db_instance.db["meta_analyses"].insert_one(meta_analysis)
    meta_analysis["_id"] = str(result.inserted_id)
    return meta_analysis

async def get_meta_analysis(meta_analysis_id: str, owner_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get a meta-analysis by ID"""
    query = {"meta_analysis_id": meta_analysis_id}
    if owner_id:
        query["owner_id"] = owner_id
    ma = await db_instance.db["meta_analyses"].find_one(query)
    if ma:
        ma["_id"] = str(ma.get("_id", ""))
    return ma

async def add_study_to_meta_analysis(meta_analysis_id: str, study_id: str, owner_id: Optional[str] = None) -> bool:
    """Add a study to a meta-analysis"""
    query = {"meta_analysis_id": meta_analysis_id}
    if owner_id:
        query["owner_id"] = owner_id
    result = await db_instance.db["meta_analyses"].update_one(
        query,
        {
            "$push": {"studies": study_id},
            "$inc": {"study_count": 1},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    return result.modified_count > 0

async def get_studies_by_meta_analysis(meta_analysis_id: str, owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all studies in a meta-analysis"""
    query: Dict[str, Any] = {"meta_analysis_id": meta_analysis_id}
    if owner_id:
        query["owner_id"] = owner_id
    cursor = db_instance.db["studies"].find(query)
    studies = await cursor.to_list(length=None)
    for study in studies:
        study["_id"] = str(study.get("_id", ""))
    return studies

async def list_all_meta_analyses(owner_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all meta-analyses"""
    query: Dict[str, Any] = {}
    if owner_id:
        query["owner_id"] = owner_id
    cursor = db_instance.db["meta_analyses"].find(query).sort("created_at", -1)
    mas = await cursor.to_list(length=None)
    for ma in mas:
        ma["_id"] = str(ma.get("_id", ""))
    return mas

async def delete_meta_analysis(meta_analysis_id: str, owner_id: Optional[str] = None) -> bool:
    """Delete a meta-analysis and all associated studies"""
    try:
        # Build query to ensure user owns this meta-analysis
        query: Dict[str, Any] = {"meta_analysis_id": meta_analysis_id}
        if owner_id:
            query["owner_id"] = owner_id
        
        # Delete all studies associated with this meta-analysis
        await db_instance.db["studies"].delete_many(query)
        
        # Delete the meta-analysis itself
        result = await db_instance.db["meta_analyses"].delete_one(query)
        
        return result.deleted_count > 0
    except Exception as e:
        print(f"Error deleting meta-analysis {meta_analysis_id}: {e}")
        return False
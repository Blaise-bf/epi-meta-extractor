"""
Epi Meta Extractor Backend

Entry point for the FastAPI application.
Run with: uvicorn backend.main:app --reload
"""

from backend.app import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

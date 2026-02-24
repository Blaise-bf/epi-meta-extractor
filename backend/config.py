from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URI: str = "mongodb+srv://farmtodo:farmtododemo@cluster0.aze7zmk.mongodb.net/todo?appName=Cluster0"
    MONGODB_DB_NAME: str = "todo"
    
    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION_NAME: str = "epi_studies"
    
    # LLM Provider Selection ("openai" or "deepseek")
    LLM_PROVIDER: str = "deepseek"
    
    # DeepSeek Configuration (preferred for testing)
    DEEPSEEK_API_KEY: str = ""  # Get from https://platform.deepseek.com
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_API_URL: str = "https://api.deepseek.com/v1"
    
    # OpenAI Configuration (for extraction and embeddings)
    OPENAI_API_KEY: str = ""  # Required for OpenAI extraction or embeddings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536  # For text-embedding-3-small

    
    # App
    UPLOAD_DIR: str = "data/raw_pdfs"
    TEMP_DIR: str = "tmp"
    APP_NAME: str = "Epi Meta Extractor"

    # Auth
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours (was 15 minutes)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MAGIC_LINK_EXPIRE_MINUTES: int = 15
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    COOKIE_SECURE: bool = False

    # SMTP (magic-link email)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@epimeta.local"
    SMTP_TLS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env file

    


settings = Settings()

import os
from pathlib import Path
from typing import List, Set
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "documind.db"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "DocuMind AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "documind-ai-super-secret-key-change-in-production-2026"

    # Database
    DATABASE_URL: str = f"sqlite:///{DB_PATH.as_posix()}"
    DATABASE_ECHO: bool = False

    # Storage
    STORAGE_DIR: Path = DATA_DIR / "uploads"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".txt"}
    ALLOWED_MIME_TYPES: Set[str] = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    }

    # OCR Engine
    # 'mock', 'paddle', or 'auto'
    OCR_PROVIDER: str = "mock"
    OCR_LANG: str = "en"
    OCR_USE_GPU: bool = False
    OCR_DPI: int = 200

    # Confidence & Validation
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.70
    CONFIDENCE_WEIGHT_OCR: float = 0.35
    CONFIDENCE_WEIGHT_EXTRACTION: float = 0.40
    CONFIDENCE_WEIGHT_VALIDATION: float = 0.25

    # LLM / Ollama (Optional local extraction fallback)
    OLLAMA_ENABLED: bool = False
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:8b"

    # Security
    ENABLE_MASKING: bool = True
    CORS_ORIGINS: List[str] = ["*"]


settings = Settings()

# Ensure directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
Path("./data").mkdir(parents=True, exist_ok=True)


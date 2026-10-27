"""Application configuration module loaded from environment variables."""
import os
from typing import List, Union
from dotenv import load_dotenv

# Pre-load .env file if it exists (check current working dir and backend folder)
load_dotenv()
backend_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
if os.path.exists(backend_env):
    load_dotenv(backend_env)

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            case_sensitive=False
        )

        # Database
        SUPABASE_DB_URL: str = os.getenv(
            "SUPABASE_DB_URL",
            "postgresql://postgres:postgres@localhost:5432/brandprint"
        )

        # AI Services
        GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        # JWT Authentication
        SECRET_KEY: str = os.getenv(
            "SECRET_KEY",
            "brandprint-ai-super-secret-key-change-in-production-min-32-chars"
        )
        ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
        ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

        # CORS & Environment
        ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
        FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
        CORS_ORIGINS: List[str] = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

except ImportError:
    # Fallback to standard Pydantic BaseModel if pydantic-settings is not yet installed
    from pydantic import BaseModel, Field

    class Settings(BaseModel):
        SUPABASE_DB_URL: str = Field(
            default_factory=lambda: os.getenv(
                "SUPABASE_DB_URL",
                "postgresql://postgres:postgres@localhost:5432/brandprint"
            )
        )
        GEMINI_API_KEY: str = Field(
            default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
        )
        OLLAMA_BASE_URL: str = Field(
            default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        SECRET_KEY: str = Field(
            default_factory=lambda: os.getenv(
                "SECRET_KEY",
                "brandprint-ai-super-secret-key-change-in-production-min-32-chars"
            )
        )
        ALGORITHM: str = Field(
            default_factory=lambda: os.getenv("ALGORITHM", "HS256")
        )
        ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
            default_factory=lambda: int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
        )
        ENVIRONMENT: str = Field(
            default_factory=lambda: os.getenv("ENVIRONMENT", "development")
        )
        FRONTEND_URL: str = Field(
            default_factory=lambda: os.getenv("FRONTEND_URL", "http://localhost:5173")
        )
        CORS_ORIGINS: List[str] = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]


settings = Settings()

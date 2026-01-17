"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"

    # Security
    secret_key: str
    api_key_salt: str

    # CORS
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"

    # Redis (for ARQ worker)
    redis_url: str = "redis://127.0.0.1:6379"

    # Supabase Storage
    supabase_url: Optional[str] = None
    supabase_secret_key: Optional[str] = None  # Secret key (sb_secret_...) for server-side operations

    # Video Generation Settings
    video_resolution_width: int = 1280
    video_resolution_height: int = 720
    video_fps: int = 2
    video_max_duration_seconds: int = 300  # 5 minutes

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

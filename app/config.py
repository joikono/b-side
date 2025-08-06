"""Application configuration settings."""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings


class Settings(BaseSettings):
    # App settings
    app_name: str = "MIDI Analysis API"
    app_version: str = "2.1.0"
    app_description: str = "Streamlined MIDI analysis with FORCED 8-chord rule for frontend uploads"
    
    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = True
    log_level: str = "info"
    
    # CORS settings
    cors_origins: List[str] = ["*"]
    
    # Directory paths
    generated_arrangements_dir: str = "astro-midi-app/public/generated_arrangements"
    generated_visualizations_dir: str = "generated_visualizations"
    
    # OpenAI settings
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-3.5-turbo"
    openai_max_tokens: int = 100
    openai_timeout: float = 30.0
    
    # Analysis settings
    default_segment_size: int = 2
    default_tolerance_beats: float = 0.15
    default_bpm: int = 100
    
    class Config:
        env_file = ".env"


# Global settings instance
settings = Settings()
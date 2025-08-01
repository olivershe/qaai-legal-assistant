"""
Configuration management for QaAI using pydantic-settings.

Following CLAUDE.md specifications for environment variable handling
and DIFC-first defaults.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings with DIFC-first defaults."""
    
    # Model Providers
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    
    # Default Model Configuration - following PRP routing strategy
    default_planner_model: str = Field("o1", env="DEFAULT_PLANNER_MODEL")
    default_drafter_model: str = Field("gpt-4.1", env="DEFAULT_DRAFTER_MODEL") 
    default_verifier_model: str = Field("claude-3.7-sonnet", env="DEFAULT_VERIFIER_MODEL")
    
    # Storage & Database
    storage_path: Path = Field(Path("./data/files"), env="STORAGE_PATH")
    db_url: str = Field("sqlite+aiosqlite:///./data/qaai.db", env="DB_URL")
    vector_store: str = Field("faiss", env="VECTOR_STORE")
    index_dir: Path = Field(Path("./data/index"), env="INDEX_DIR")
    
    # RAG Configuration
    embeddings_backend: str = Field("sentence-transformers", env="EMBEDDINGS_BACKEND")
    embeddings_model: str = Field("all-MiniLM-L6-v2", env="EMBEDDINGS_MODEL")
    chunk_size: int = Field(800, env="CHUNK_SIZE")
    chunk_overlap: int = Field(120, env="CHUNK_OVERLAP")
    
    # DIFC Configuration - jurisdiction-first approach
    default_jurisdiction: str = Field("DIFC", env="DEFAULT_JURISDICTION")
    citation_threshold: float = Field(0.25, env="CITATION_THRESHOLD")
    
    # Application
    app_env: str = Field("dev", env="APP_ENV")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    backend_url: str = Field("http://localhost:8000", env="BACKEND_URL")
    
    # Optional: Supabase integration
    supabase_url: Optional[str] = Field(None, env="SUPABASE_URL")
    supabase_anon_key: Optional[str] = Field(None, env="SUPABASE_ANON_KEY")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Validate critical settings
        if not self.openai_api_key and not self.anthropic_api_key:
            raise ValueError("At least one API key (OpenAI or Anthropic) must be provided")
    
    @property
    def database_path(self) -> Path:
        """Extract database file path from DB_URL."""
        if "sqlite" in self.db_url:
            # Extract path from sqlite+aiosqlite:///./data/qaai.db
            path_part = self.db_url.split("///")[-1]
            return Path(path_part)
        return Path("./data/qaai.db")
    
    @property 
    def available_models(self) -> dict[str, List[str]]:
        """Return available models based on configured API keys."""
        models = {}
        
        if self.openai_api_key:
            models["openai"] = ["gpt-4.1", "o1", "o3", "gpt-4-turbo"]
            
        if self.anthropic_api_key:
            models["anthropic"] = ["claude-3.7-sonnet", "claude-3-opus", "claude-3-haiku"]
            
        return models
    
    @property
    def default_knowledge_sources(self) -> List[str]:
        """DIFC-first knowledge sources as specified in requirements."""
        return ["DIFC_LAWS", "DFSA_RULEBOOK", "DIFC_COURTS_RULES", "VAULT"]

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
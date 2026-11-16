"""
Settings read from the environment (or a .env file). Every tunable value lives here.

    DATA_PATH=data/raw/marketing_campaign.csv
    ARTIFACTS_DIR=artifacts
    LLM_PROVIDER=gemini   GEMINI_API_KEY=...   LLM_MODEL=gemini-3.8-flash
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Data and artifacts
    data_path: Path = Path("data/raw/marketing_campaign.csv")
    artifacts_dir: Path = Path("artifacts")
    artifact_version: str = ""  # empty -> the version named in artifacts/LATEST

    # Training
    random_state: int = 42
    test_size: float = 0.2
    cv_folds: int = 5
    k_min: int = 2
    k_max: int = 8
    n_segments: int = 0  # 0 -> pick k by silhouette among k >= 3; set to force a value

    # LLM (optional: the app works without a key)
    llm_provider: str = "gemini"
    llm_model: str = ""  # empty -> provider default
    llm_fallback_model: str | None = None  # None -> provider default; empty -> no fallback
    gemini_api_key: str = ""
    llm_timeout_s: float = 20.0  # per attempt; a slow model then falls back once

    # API
    frontend_dist: Path = Path("frontend/dist")  # built web app served at / when present
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

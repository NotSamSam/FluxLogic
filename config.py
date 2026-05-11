"""
FluxLogic - Configuration Management
=====================================
Centralized configuration using pydantic-settings for strict validation
of environment variables and application defaults.
"""

from __future__ import annotations

import os
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class FluxLogicSettings(BaseSettings):
    """
    Application-wide settings loaded from environment variables or `.env` file.

    All values are validated at startup via pydantic so that configuration
    errors surface immediately rather than at runtime.
    """

    # ── Application ──────────────────────────────────────────────────
    app_name: str = Field(default="FluxLogic", description="Display name of the application")
    app_version: str = Field(default="0.1.0", description="Semantic version")
    debug: bool = Field(default=False, description="Enable verbose logging")

    # ── API Defaults ─────────────────────────────────────────────────
    default_timeout: int = Field(
        default=30,
        ge=1,
        le=120,
        description="Default HTTP timeout in seconds for outbound API calls",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts for failed requests",
    )
    retry_backoff_factor: float = Field(
        default=0.5,
        ge=0.1,
        le=5.0,
        description="Exponential backoff multiplier between retries",
    )

    # ── Webhook Server ───────────────────────────────────────────────
    webhook_port: int = Field(
        default=8501,
        ge=1024,
        le=65535,
        description="Port for the simulated webhook listener",
    )
    webhook_secret: Optional[str] = Field(
        default=None,
        description="HMAC secret for webhook payload verification",
    )

    # ── Processing Limits ────────────────────────────────────────────
    max_upload_size_mb: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum file upload size in megabytes",
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Number of records to send per API batch call",
    )

    # ── Logging ──────────────────────────────────────────────────────
    log_level: str = Field(default="INFO", description="Python logging level")
    log_format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        description="Logging format string",
    )

    # ── Validators ───────────────────────────────────────────────────
    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return upper

    model_config = {
        "env_prefix": "FLUXLOGIC_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# ── Singleton accessor ───────────────────────────────────────────────
_settings: Optional[FluxLogicSettings] = None


def get_settings() -> FluxLogicSettings:
    """Return the cached application settings (created once)."""
    global _settings
    if _settings is None:
        _settings = FluxLogicSettings()
    return _settings

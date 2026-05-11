from __future__ import annotations

import os
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class FluxLogicSettings(BaseSettings):
    app_name: str = Field(default="FluxLogic")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)

    default_timeout: int = Field(default=30, ge=1, le=120)
    max_retries: int = Field(default=3, ge=0, le=10)
    retry_backoff_factor: float = Field(default=0.5, ge=0.1, le=5.0)

    webhook_port: int = Field(default=8501, ge=1024, le=65535)
    webhook_secret: Optional[str] = Field(default=None)

    max_upload_size_mb: int = Field(default=50, ge=1, le=500)
    batch_size: int = Field(default=100, ge=1, le=10000)

    log_level: str = Field(default="INFO")
    log_format: str = Field(
        default="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

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


_settings: Optional[FluxLogicSettings] = None


def get_settings() -> FluxLogicSettings:
    global _settings
    if _settings is None:
        _settings = FluxLogicSettings()
    return _settings

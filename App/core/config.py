"""Validated environment configuration, loaded once at application startup."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, HttpUrl, field_validator


class Settings(BaseModel):
    pokeapi_base_url: HttpUrl = HttpUrl("https://pokeapi.co/api/v2/")
    pokeapi_timeout_seconds: float = Field(default=5, gt=0, le=30)
    pokeapi_retries: int = Field(default=1, ge=0, le=2)
    cache_ttl_seconds: float = Field(default=3600, gt=0)
    cache_stale_seconds: float = Field(default=86400, ge=0)
    cache_max_entries: int = Field(default=1000, ge=18, le=100000)
    candidates_per_type: int = Field(default=5, ge=1, le=10)
    rate_limit_per_minute: int = Field(default=30, ge=1, le=10000)
    log_level: str = "INFO"

    @field_validator("pokeapi_base_url")
    @classmethod
    def secure_url(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https" or value.username or value.password or value.query or value.fragment:
            raise ValueError("Use an HTTPS base URL without credentials, query or fragment")
        return value

    @field_validator("log_level")
    @classmethod
    def valid_level(cls, value: str) -> str:
        value = value.upper()
        if value not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Invalid log level")
        return value

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)
        return cls(**{key: os.environ[key.upper()] for key in cls.model_fields if key.upper() in os.environ})

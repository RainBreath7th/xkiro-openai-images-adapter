from __future__ import annotations

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    api_key: str = Field(min_length=1)
    xkiro_api_key: str = Field(min_length=1)
    xkiro_base_url: AnyHttpUrl = "https://api.xkiro.com"
    port: int = Field(default=5080, ge=1, le=65535)
    upstream_timeout_seconds: float = Field(default=300.0, gt=0)
    strict_parameters: bool = False
    max_body_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    log_level: str = "INFO"

    @field_validator("xkiro_base_url", mode="after")
    @classmethod
    def validate_base_url(cls, value: AnyHttpUrl) -> AnyHttpUrl:
        if value.path not in ("", "/") or value.query or value.fragment:
            raise ValueError("XKIRO_BASE_URL must not include a path, query, or fragment")
        return value

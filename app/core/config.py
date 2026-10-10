"""
app/core/config.py
------------------
Centralised application settings loaded from environment variables
or a local .env file via Pydantic-Settings.

All policy thresholds are configurable so no business rule is hard-coded.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Company / Policy ─────────────────────────────────────────────────────
    COMPANY_TIMEZONE: str = "Asia/Kolkata"
    MIN_OFFICE_DAYS_PER_WEEK: int = 3
    MIN_WEEKLY_WORKING_HOURS: float = 15.0
    MIN_AVERAGE_HOURS_PER_DAY: float = 5.0

    # ── SMTP ─────────────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    EMAIL_MOCK_MODE: bool = False  # True → no real emails during tests

    @model_validator(mode="after")
    def set_default_from_email(self) -> Settings:
        if not self.SMTP_FROM_EMAIL:
            self.SMTP_FROM_EMAIL = self.SMTP_USERNAME
        return self

    # ── Scheduler ────────────────────────────────────────────────────────────
    ATTENDANCE_EVALUATION_DAY: str = "monday"
    ATTENDANCE_EVALUATION_TIME: str = "09:00"

    @field_validator("ATTENDANCE_EVALUATION_DAY")
    @classmethod
    def validate_day(cls, v: str) -> str:
        valid = {
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
        }
        if v.lower() not in valid:
            raise ValueError(f"ATTENDANCE_EVALUATION_DAY must be one of {valid}")
        return v.lower()

    @field_validator("ATTENDANCE_EVALUATION_TIME")
    @classmethod
    def validate_time(cls, v: str) -> str:
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("ATTENDANCE_EVALUATION_TIME must be HH:MM")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("ATTENDANCE_EVALUATION_TIME must be a valid 24-h time")
        return v

    @property
    def evaluation_hour(self) -> int:
        return int(self.ATTENDANCE_EVALUATION_TIME.split(":")[0])

    @property
    def evaluation_minute(self) -> int:
        return int(self.ATTENDANCE_EVALUATION_TIME.split(":")[1])


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()

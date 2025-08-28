from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Config:
    bot_token: str
    gemini_api_key: Optional[str]
    max_file_size_mb: int = 25
    # Queue/anti-spam
    max_concurrent_jobs: int = 1
    queue_limit: int = 50
    per_user_cooldown_s: int = 15
    per_user_max_pending: int = 1
    est_seconds_per_job: int = 30
    # Dynamic estimation/timeouts
    est_seconds_convert_per_file: int = 5
    est_seconds_ai_per_file: int = 2
    gemini_timeout_s: int = 45
    gemini_max_retries: int = 2


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN env var is required")
    gemini = os.getenv("GEMINI_API_KEY") or None
    def _int(name: str, default: int) -> int:
        try:
            return int(os.getenv(name, str(default)))
        except ValueError:
            return default

    return Config(
        bot_token=token,
        gemini_api_key=gemini,
        max_file_size_mb=_int("MAX_FILE_SIZE_MB", 25),
        max_concurrent_jobs=_int("MAX_CONCURRENT_JOBS", 1),
        queue_limit=_int("QUEUE_LIMIT", 50),
        per_user_cooldown_s=_int("PER_USER_COOLDOWN_S", 15),
        per_user_max_pending=_int("PER_USER_MAX_PENDING", 1),
        est_seconds_per_job=_int("EST_SECONDS_PER_JOB", 30),
    est_seconds_convert_per_file=_int("EST_SECONDS_CONVERT_PER_FILE", 5),
    est_seconds_ai_per_file=_int("EST_SECONDS_AI_PER_FILE", 2),
    gemini_timeout_s=_int("GEMINI_TIMEOUT_S", 45),
    gemini_max_retries=_int("GEMINI_MAX_RETRIES", 2),
    )

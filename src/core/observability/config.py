from __future__ import annotations

import os
from dataclasses import dataclass

from src.utils import load_config


@dataclass(frozen=True)
class LangfuseSettings:
    enabled: bool
    host: str | None
    public_key: str | None
    secret_key: str | None
    environment: str | None
    sample_rate: float | None


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return default


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def get_langfuse_settings() -> LangfuseSettings:
    app_cfg = load_config()
    raw_cfg = app_cfg.get("observability", {}).get("langfuse", {})

    host_env = str(raw_cfg.get("host_env", "LANGFUSE_HOST"))
    public_key_env = str(raw_cfg.get("public_key_env", "LANGFUSE_PUBLIC_KEY"))
    secret_key_env = str(raw_cfg.get("secret_key_env", "LANGFUSE_SECRET_KEY"))
    environment_env = str(raw_cfg.get("environment_env", "LANGFUSE_ENV"))

    host = os.getenv(host_env) or raw_cfg.get("host")
    public_key = os.getenv(public_key_env)
    secret_key = os.getenv(secret_key_env)
    environment = os.getenv(environment_env) or raw_cfg.get("environment") or os.getenv("APP_ENV")
    sample_rate = _as_float(raw_cfg.get("sample_rate", 1.0))

    return LangfuseSettings(
        enabled=_as_bool(raw_cfg.get("enabled", False), default=False),
        host=host if isinstance(host, str) and host else None,
        public_key=public_key if public_key else None,
        secret_key=secret_key if secret_key else None,
        environment=environment if isinstance(environment, str) and environment else None,
        sample_rate=sample_rate,
    )

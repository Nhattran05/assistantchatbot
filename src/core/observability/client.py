from __future__ import annotations

import logging
from typing import Any

from src.core.observability.config import get_langfuse_settings

logger = logging.getLogger(__name__)
_LANGFUSE_INITIALIZED = False


def get_langfuse_client() -> Any | None:
    settings = get_langfuse_settings()
    if not settings.enabled:
        return None

    if not settings.public_key or not settings.secret_key:
        logger.warning(
            "Langfuse tracing is enabled but credentials are missing. "
            "Set LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY."
        )
        return None

    try:
        from langfuse import Langfuse, get_client  # noqa: PLC0415
    except ImportError:
        logger.exception("Langfuse package is not installed.")
        return None

    global _LANGFUSE_INITIALIZED
    if not _LANGFUSE_INITIALIZED:
        init_kwargs: dict[str, Any] = {
            "public_key": settings.public_key,
            "secret_key": settings.secret_key,
            "tracing_enabled": settings.enabled,
        }
        if settings.host:
            init_kwargs["host"] = settings.host
        if settings.environment:
            init_kwargs["environment"] = settings.environment
        if settings.sample_rate is not None:
            init_kwargs["sample_rate"] = settings.sample_rate

        Langfuse(**init_kwargs)
        _LANGFUSE_INITIALIZED = True

    return get_client()


def flush_langfuse() -> None:
    client = get_langfuse_client()
    if client is None:
        return

    try:
        client.flush()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to flush Langfuse events.")

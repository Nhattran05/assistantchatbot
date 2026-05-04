from __future__ import annotations

import logging
from typing import Any

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.runnables import RunnableConfig

from src.core.observability.client import get_langfuse_client

logger = logging.getLogger(__name__)


def get_langfuse_callbacks() -> list[BaseCallbackHandler]:
    client = get_langfuse_client()
    if client is None:
        return []

    try:
        from langfuse.langchain import CallbackHandler  # noqa: PLC0415
    except ImportError:
        logger.exception("Langfuse LangChain callback import failed.")
        return []

    return [CallbackHandler()]


def build_langchain_invoke_config(
    config: RunnableConfig | None,
    *,
    extra_metadata: dict[str, Any] | None = None,
) -> RunnableConfig | None:
    invoke_config: RunnableConfig = {}

    if config:
        callbacks = config.get("callbacks")
        if callbacks is not None:
            invoke_config["callbacks"] = callbacks

        metadata = dict(config.get("metadata") or {})
    else:
        metadata = {}

    if extra_metadata:
        metadata.update(extra_metadata)

    if metadata:
        invoke_config["metadata"] = metadata

    return invoke_config or None

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from src.core.observability.client import get_langfuse_client

logger = logging.getLogger(__name__)


@contextmanager
def start_observation(
    name: str,
    *,
    input_data: Any | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[Any | None]:
    client = get_langfuse_client()
    if client is None:
        yield None
        return

    kwargs: dict[str, Any] = {"name": name}
    if input_data is not None:
        kwargs["input"] = input_data
    if metadata:
        kwargs["metadata"] = metadata

    try:
        observation_cm = client.start_as_current_observation(**kwargs)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to create Langfuse observation '%s'.", name)
        yield None
        return

    with observation_cm as observation:
        yield observation

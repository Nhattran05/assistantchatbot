from __future__ import annotations

from typing import Any
from uuid import uuid4


def new_trace_id() -> str:
    return uuid4().hex


def _trim_text(value: str, max_chars: int = 500) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}..."


def build_workflow_trace_metadata(
    *,
    nl_input: str,
    workflow_name: str,
    route_path: str,
    request_method: str,
    db_type: str,
    trace_id: str,
) -> dict[str, Any]:
    return {
        "trace_id": trace_id,
        "workflow_name": workflow_name,
        "route_path": route_path,
        "request_method": request_method,
        "db_type": db_type,
        "nl_input_preview": _trim_text(nl_input),
    }


def build_step_metadata(base_metadata: dict[str, Any], step_name: str) -> dict[str, Any]:
    step_metadata = dict(base_metadata)
    step_metadata["step_name"] = step_name
    return step_metadata

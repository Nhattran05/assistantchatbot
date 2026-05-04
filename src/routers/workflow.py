"""
src/routers/workflow.py
───────────────────────
HTTP layer for the NLQ pipeline.

All business logic lives in NlqWorkflow (src/core/workflows/nlq_workflow.py).
This router only handles:
  - HTTP request/response shape
  - Injecting the startup DB connection into the workflow
  - Mapping workflow state to the API response

Endpoint
────────
POST /workflow
    Run the full NLQ pipeline: guardrail → schema linking → SQL generation.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.core.observability import (
    build_workflow_trace_metadata,
    flush_langfuse,
    get_langfuse_callbacks,
    new_trace_id,
    start_observation,
)
from src.core.workflows.factory import WorkflowFactory

router = APIRouter(prefix="/workflow", tags=["Workflow"])


# ── Request / Response models ─────────────────────────────────────────────────

class WorkflowRequest(BaseModel):
    nl_input: str = Field(..., description="Natural language input from user")


class GuardrailResult(BaseModel):
    verdict: str
    block_reason: str
    warnings: list[str]
    message: str


class WorkflowResponse(BaseModel):
    guardrail: GuardrailResult
    schema_linking: dict | None = None
    schema_linking_raw: str | None = None
    sql_query: str | None = None
    sql_status: str | None = None
    sql_result: list | None = None
    sql_error_message: str | None = None
    reflection: dict | None = None
    reflection_raw: str | None = None


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("", response_model=WorkflowResponse, summary="Run full NLQ pipeline")
async def run_workflow(body: WorkflowRequest, request: Request) -> WorkflowResponse:
    """
    Execute the full NLQ-to-SQL pipeline:
      1. Guardrail – blocks prompt injection attempts
      2. Schema Linking – identifies relevant tables/columns
      3. SQL Generation – generates and executes SQL with auto-retry
      4. Reflection – verify the SQL correctness using the query result and retry generation if needed.
    """
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized on startup")

    workflow_name = "nlq"
    trace_id = new_trace_id()
    trace_metadata = build_workflow_trace_metadata(
        nl_input=body.nl_input,
        workflow_name=workflow_name,
        route_path=request.url.path,
        request_method=request.method,
        db_type=type(db).__name__,
        trace_id=trace_id,
    )
    invoke_config: dict = {
        "configurable": {
            "db": db,
            "trace_id": trace_id,
            "trace_metadata": trace_metadata,
            "workflow_name": workflow_name,
        },
        "metadata": {
            "workflow_name": workflow_name,
            "langfuse_session_id": trace_id,
            "langfuse_tags": [f"workflow:{workflow_name}", "endpoint:/workflow"],
        },
    }
    callbacks = get_langfuse_callbacks()
    if callbacks:
        invoke_config["callbacks"] = callbacks

    try:
        workflow = WorkflowFactory.create(workflow_name)
        with start_observation(
            "workflow.run",
            input_data={"nl_input": body.nl_input},
            metadata=trace_metadata,
        ):
            state = await workflow.ainvoke(
                {"nl_input": body.nl_input},
                config=invoke_config,
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        flush_langfuse()

    guardrail = GuardrailResult(
        verdict=state.get("guardrail_verdict", "PASS"),
        block_reason=state.get("guardrail_block_reason", ""),
        warnings=state.get("guardrail_warnings", []),
        message=state.get("guardrail_message", ""),
    )

    schema_linking = state.get("schema_linking")
    schema_raw = state.get("schema_linking_raw") or None

    return WorkflowResponse(
        guardrail=guardrail,
        schema_linking=schema_linking,
        schema_linking_raw=schema_raw,
        sql_query=state.get("sql_query") or None,
        sql_status=state.get("sql_status") or None,
        sql_result=state.get("sql_result") or None,
        sql_error_message=state.get("sql_error_message") or None,
        reflection=state.get("reflection"),
        reflection_raw=state.get("reflection_raw"),
    )

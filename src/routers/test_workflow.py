import json
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/test-work-flow", tags=["Test Workflow"])

_DEFAULT_SCHEMA = {
    "full_name": "",
    "phone_number": "",
    "health_insurance_number": "",
    "examination_date": "",
    "age": "",
    "medical_history": "",
    "symptoms": "",
    "initial_diagnosis": "",
    "next_treatment_plan": "",
    "notes": "",
}


class WorkflowChatRequest(BaseModel):
    message: str


class WorkflowChatResponse(BaseModel):
    filled_form: dict
    docx_path: str


@router.post("/chat", response_model=WorkflowChatResponse)
async def test_workflow_chat(request: Request):
    # Read raw body and sanitize literal control characters (e.g. bare \n from
    # Swagger UI multiline textarea) that make JSON invalid before Pydantic sees it.
    raw = await request.body()
    sanitized = raw.decode("utf-8").replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    try:
        data = json.loads(sanitized)
        payload = WorkflowChatRequest(**data)
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        from src.core.workflows.factory import WorkflowFactory

        workflow = WorkflowFactory.create("form_docx_workflow")
        initial_state = {
            "messages": [],
            "user_text": payload.message,
            "form_schema": _DEFAULT_SCHEMA,
            "filled_form": "",
            "docx_path": "",
            "next": "",
            "final_answer": "",
        }
        result = await workflow.ainvoke(initial_state)

        try:
            filled_form_dict = json.loads(result.get("filled_form", "{}"))
        except json.JSONDecodeError:
            filled_form_dict = {}

        return WorkflowChatResponse(
            filled_form=filled_form_dict,
            docx_path=result.get("docx_path", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download")
async def download_docx(path: str):
    """Download a generated DOCX file by its path (returned by /chat)."""
    if not path.endswith(".docx") or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=os.path.basename(path),
    )

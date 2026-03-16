import json
import os
import shutil
import uuid

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

router = APIRouter(prefix="/conversation", tags=["Conversation"])

_DEFAULT_SCHEMA = {
    "full_name": "",
    "phone_number": "",
    "health_insurance_number": "",
    "medical_history": "",
    "symptoms": "",
    "initial_diagnosis": "",
    "next_treatment_plan": "",
    "notes": "",
    "summarize": "",
}

_UPLOAD_DIR = "outputs/uploads"


class ConversationResponse(BaseModel):
    filled_form: dict
    docx_path: str


@router.post("/analyze", response_model=ConversationResponse)
async def analyze_conversation(file: UploadFile):
    """
    Upload a WAV/FLAC recording of a 2-person conversation.
    Returns labeled transcript, filled form, and a downloadable DOCX.
    """
    # ── Validate file type ────────────────────────────────────────────
    filename = file.filename or ""
    ext = os.path.splitext(filename)[-1].lower()
    if ext not in {".wav", ".flac", ".mp3", ".m4a"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload WAV, FLAC, MP3, or M4A.",
        )

    # ── Save upload to disk ───────────────────────────────────────────
    os.makedirs(_UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    audio_path  = os.path.join(_UPLOAD_DIR, unique_name)

    try:
        with open(audio_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    finally:
        await file.close()

    # ── Run workflow ──────────────────────────────────────────────────
    try:
        from src.core.workflows.factory import WorkflowFactory

        workflow = WorkflowFactory.create("conversation_workflow")
        initial_state = {
            "audio_path":            audio_path,
            "messages":              [],
            "turns_json":            "",
            "labeled_turns_json":    "",
            "consultant_speaker_id": "",
            "customer_speaker_id":   "",
            "customer_text":         "",
            "normalized_text":       "",
            "user_text":             "",
            "form_schema":           _DEFAULT_SCHEMA,
            "filled_form":           "",
            "docx_path":             "",
            "final_answer":          "",
        }
        result = await workflow.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up the uploaded file after processing
        if os.path.exists(audio_path):
            os.remove(audio_path)

    # ── Parse results ─────────────────────────────────────────────────
    try:
        labeled_turns = json.loads(result.get("labeled_turns_json", "[]"))
    except json.JSONDecodeError:
        labeled_turns = []

    try:
        filled_form_dict = json.loads(result.get("filled_form", "{}"))
    except json.JSONDecodeError:
        filled_form_dict = {}

    return ConversationResponse(
        filled_form=filled_form_dict,
        docx_path=result.get("docx_path", ""),
    )


@router.get("/download")
async def download_docx(path: str):
    """Download the generated DOCX file by path returned from /analyze."""
    if not path.endswith(".docx") or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=os.path.basename(path),
    )

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    workflow: str | None = None


class ChatResponse(BaseModel):
    answer: str


@router.post("/", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    try:
        from src.core.workflows.factory import WorkflowFactory

        workflow = WorkflowFactory.create(name=payload.workflow)
        result = await workflow.ainvoke({"messages": [payload.message], "next": "", "final_answer": ""})
        return ChatResponse(answer=result.get("final_answer", ""))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

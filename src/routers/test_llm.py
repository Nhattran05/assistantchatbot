from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.llm.factory import LLMFactory

router = APIRouter(prefix="/test-llm", tags=["Test LLM"])


class TestChatRequest(BaseModel):
    message: str
    provider: str = "mega_llm"
    model: str | None = None


class TestChatResponse(BaseModel):
    provider: str
    model: str | None
    reply: str


@router.post("/chat", response_model=TestChatResponse)
async def test_chat(payload: TestChatRequest):
    try:
        llm = LLMFactory.create(provider=payload.provider, model=payload.model)
        from langchain_core.messages import HumanMessage

        response = await llm.ainvoke([HumanMessage(content=payload.message)])
        return TestChatResponse(
            provider=payload.provider,
            model=payload.model,
            reply=response.content,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import FastAPI


def register_routers(app: FastAPI) -> None:
    from src.routers.chat import router as chat_router
    from src.routers.conversation import router as conversation_router
    from src.routers.test_llm import router as test_llm_router
    from src.routers.test_workflow import router as test_workflow_router
    from src.routers.voice_call import router as voice_call_router
    from src.routers.livekit import router as livekit_router

    app.include_router(chat_router)
    app.include_router(test_llm_router)
    app.include_router(test_workflow_router)
    app.include_router(conversation_router)
    app.include_router(voice_call_router)
    app.include_router(livekit_router)


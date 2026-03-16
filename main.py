from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.routers import register_routers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic (DB connect, warm-up models, etc.)
    yield
    # Shutdown logic (cleanup resources)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-Agent API",
        version="0.1.0",
        description="Multi-Agent project built with LangGraph & FastAPI",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    register_routers(app)
    return app


app = create_app()

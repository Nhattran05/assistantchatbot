import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI

from src.routers import register_routers

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ------------------------------------------------------------------
    # Startup: load Gipformer engine + preload VAD + preload diarization
    # ------------------------------------------------------------------
    from src.utils import load_config
    from src.services.asr_service import load_gipformer_engine, set_engine
    from src.services.chunk_audio import preload_vad

    cfg = load_config()
    
    # Display device configuration warnings
    _log_device_configuration(cfg)

    # 1. Download + load Gipformer ONNX model
    logger.info("[Startup] Loading Gipformer engine...")
    gipformer_engine = load_gipformer_engine(cfg)
    app.state.gipformer_engine = gipformer_engine
    # Set module-level singleton so ASRService() works without injection
    set_engine(gipformer_engine)
    logger.info("[Startup] ✓ Gipformer engine ready (quantize=%s)", gipformer_engine.quantize)

    # 2. Preload Silero VAD ONNX (avoids cold-start on first request)
    logger.info("[Startup] Preloading Silero VAD (ONNX)...")
    preload_vad()
    logger.info("[Startup] ✓ Silero VAD preloaded")

    # 3. Preload diarization model (NeMo SortFormer) — only if .nemo file exists
    _preload_diarization(cfg)
    
    # Final device summary
    _log_device_summary()

    yield

    # ------------------------------------------------------------------
    # Shutdown: free resources
    # ------------------------------------------------------------------
    logger.info("[Shutdown] Releasing Gipformer engine resources")
    del app.state.gipformer_engine


def _log_device_configuration(cfg: dict) -> None:
    """Hiển thị device configuration khi server khởi động."""
    logger.info("="*60)
    
    # Check PyTorch CUDA
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("PyTorch: CUDA available (%s)", torch.cuda.get_device_name(0))
        else:
            logger.warning("PyTorch: CUDA NOT available - using CPU")
    except ImportError:
        logger.warning("PyTorch: Not installed")
    
    # Check ONNX Runtime
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        if "CUDAExecutionProvider" in providers:
            logger.info("ONNX Runtime: CUDA provider available")
        else:
            logger.warning("ONNX Runtime: CUDA provider NOT available - using CPU")
    except ImportError:
        logger.warning("ONNX Runtime: Not installed")
    
    # Show config
    models_cfg = cfg.get("models", {})
    gipformer_cfg = cfg.get("gipformer", {})
    logger.info("Config: diarization=%s, gipformer=%s", 
                models_cfg.get("device", "auto"),
                gipformer_cfg.get("provider", "auto"))
    logger.info("="*60)


def _log_device_summary() -> None:
    """Hiển thị tóm tắt device sau khi load models."""
    logger.info("="*60)
    try:
        import torch
        if torch.cuda.is_available():
            logger.info("SERVER READY - Running on GPU")
        else:
            logger.warning("SERVER READY - Running on CPU (slower performance)")
            logger.warning("Install CUDA + onnxruntime-gpu for GPU support")
    except ImportError:
        pass
    logger.info("="*60)


def _preload_diarization(cfg: dict) -> None:
    """
    Preload NeMo SortFormer diarization model at startup.
    Skips silently if the .nemo file doesn't exist (safe for dev/testing).
    """
    import os
    from src.services.diarization_service import (
        _load_diar_model,
        _DEFAULT_MODEL_PATH,
    )
    from src.services.asr_service import _resolve_path, _is_wsl

    models_cfg = cfg.get("models", {})
    model_path = _resolve_path(
        models_cfg,
        "diarization_path",
        _DEFAULT_MODEL_PATH,
    )
    device_config = models_cfg.get("device", "auto")

    if not os.path.exists(model_path):
        logger.warning(
            "[Startup] Diarization model not found at '%s' — skipping preload. "
            "First /conversation/analyze request will be slow.",
            model_path,
        )
        return

    try:
        logger.info("[Startup] Preloading diarization model from: %s", model_path)
        _load_diar_model(model_path, device_config)  # lru_cache — loaded once, reused forever
        logger.info("[Startup] ✓ Diarization model preloaded")
    except Exception as exc:
        logger.warning(
            "[Startup] Diarization preload failed (%s) — will lazy-load on first request.",
            exc,
        )


def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-Agent API (Gipformer STT)",
        version="2.0.0",
        description="Multi-Agent project with Gipformer RNNT ASR — built with LangGraph & FastAPI",
        lifespan=lifespan,
    )

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "ok"}

    register_routers(app)
    return app


app = create_app()

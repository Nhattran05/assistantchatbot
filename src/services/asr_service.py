"""
ASRService (Gipformer RNNT)
---------------------------
Wraps the Gipformer 65M RNNT model (sherpa-onnx) as a singleton engine.

Engine: g-group-ai-lab/gipformer-65M-rnnt downloaded from HuggingFace Hub.
Backend: sherpa-onnx OfflineRecognizer (no NeMo, no KenLM, no torch required).

Usage:
    # At startup (called from main.py lifespan):
    engine = load_gipformer_engine(cfg)
    app.state.gipformer_engine = engine

    # In services/routers:
    engine: GipformerEngine = request.app.state.gipformer_engine
    text = engine.transcribe_file("audio.wav")
"""
from __future__ import annotations

import asyncio
import logging
import os
import platform
import tempfile
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

# ── Module-level engine singleton ────────────────────────────────────────────
# Set once at startup (main.py lifespan), then get_engine() hoạt động
# trong bất kỳ context nào (workflow nodes, services, etc.) — không cần inject.

_engine_ref: Optional["GipformerEngine"] = None


def set_engine(engine: "GipformerEngine") -> None:
    """Call once from main.py lifespan after load_gipformer_engine()."""
    global _engine_ref
    _engine_ref = engine
    logger.info("[ASR] Global engine singleton set (id=%s)", id(engine))


def get_engine() -> "GipformerEngine":
    """Get the global GipformerEngine. Raises RuntimeError if not initialized."""
    engine = _engine_ref
    if engine is None:
        raise RuntimeError(
            "GipformerEngine not initialized. "
            "Call set_engine() from main.py lifespan at startup."
        )
    return engine


# Gipformer ONNX file names per quantize mode
_ONNX_FILES = {
    "fp32": {
        "encoder": "encoder-epoch-35-avg-6.onnx",
        "decoder": "decoder-epoch-35-avg-6.onnx",
        "joiner":  "joiner-epoch-35-avg-6.onnx",
    },
    "int8": {
        "encoder": "encoder-epoch-35-avg-6.int8.onnx",
        "decoder": "decoder-epoch-35-avg-6.int8.onnx",
        "joiner":  "joiner-epoch-35-avg-6.int8.onnx",
    },
}

_SAMPLE_RATE = 16_000
_FEATURE_DIM = 80
_TARGET_SR   = 16_000


# ── WSL helper (giữ lại cho diarization_service) ────────────────────────────

def _is_wsl() -> bool:
    """Trả về True nếu đang chạy trong WSL."""
    if platform.system() != "Linux":
        return False
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def _resolve_path(cfg: dict, key: str, default: str = "") -> str:
    """Lấy path từ config, ưu tiên key_wsl khi chạy trong WSL."""
    if _is_wsl():
        wsl_val = cfg.get(f"{key}_wsl", "")
        if wsl_val:
            return wsl_val
    return cfg.get(key, default)


# ── Batching engine (từ gipformer serve.py) ──────────────────────────────────


@dataclass
class _PendingRequest:
    samples: np.ndarray
    sample_rate: int
    future: asyncio.Future = field(default=None)


class BatchingEngine:
    """Collects incoming requests and processes them in micro-batches."""

    def __init__(self, recognizer, max_batch_size: int = 16, max_wait_ms: float = 100):
        self.recognizer = recognizer
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self._queue: list = []
        self._lock = asyncio.Lock()
        self._timer_task: Optional[asyncio.Task] = None

    async def submit(self, samples: np.ndarray, sample_rate: int) -> str:
        loop = asyncio.get_running_loop()
        req = _PendingRequest(samples=samples, sample_rate=sample_rate, future=loop.create_future())

        batch_to_process = None
        async with self._lock:
            self._queue.append(req)
            if len(self._queue) >= self.max_batch_size:
                batch_to_process = self._queue[:]
                self._queue.clear()
                if self._timer_task and not self._timer_task.done():
                    self._timer_task.cancel()
                    self._timer_task = None
            elif len(self._queue) == 1:
                self._timer_task = asyncio.create_task(self._wait_and_flush())

        if batch_to_process is not None:
            asyncio.create_task(self._process_batch(batch_to_process))

        return await req.future

    async def _wait_and_flush(self):
        await asyncio.sleep(self.max_wait_ms / 1000.0)
        batch = None
        async with self._lock:
            if self._queue:
                batch = self._queue[:]
                self._queue.clear()
                self._timer_task = None
        if batch:
            await self._process_batch(batch)

    async def _process_batch(self, batch: list[_PendingRequest]):
        loop = asyncio.get_running_loop()
        try:
            results = await loop.run_in_executor(None, self._infer_batch, batch)
            for req, text in zip(batch, results):
                if not req.future.done():
                    req.future.set_result(text)
        except Exception as e:
            for req in batch:
                if not req.future.done():
                    req.future.set_exception(e)

    def _infer_batch(self, batch: list[_PendingRequest]) -> list[str]:
        import sherpa_onnx
        streams = []
        for req in batch:
            stream = self.recognizer.create_stream()
            stream.accept_waveform(req.sample_rate, req.samples)
            streams.append(stream)
        self.recognizer.decode_streams(streams)
        return [s.result.text.strip() for s in streams]


# ── GipformerEngine ──────────────────────────────────────────────────────────


class GipformerEngine:
    """
    Singleton ASR engine wrapping sherpa-onnx OfflineRecognizer.

    Created once at startup via load_gipformer_engine() and stored in
    app.state.gipformer_engine.
    """

    def __init__(
        self,
        recognizer,
        engine: BatchingEngine,
        quantize: str,
    ):
        self.recognizer = recognizer
        self.engine = engine
        self.quantize = quantize

    # ── Sync transcription (for batch_worker thread pool) ────────────────

    def transcribe_wav_sync(self, wav_path: str) -> str:
        """Transcribe a single WAV file synchronously (runs in executor)."""
        import sherpa_onnx
        samples, sr = sf.read(wav_path, dtype="float32")
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        samples = _resample_linear(samples, sr, _SAMPLE_RATE)

        stream = self.recognizer.create_stream()
        stream.accept_waveform(_SAMPLE_RATE, samples)
        self.recognizer.decode_stream(stream)
        return stream.result.text.strip()

    def transcribe_wav_batch_sync(self, wav_paths: list[str]) -> list[str]:
        """Transcribe a batch of WAV files synchronously."""
        import sherpa_onnx
        streams = []
        for path in wav_paths:
            samples, sr = sf.read(path, dtype="float32")
            if samples.ndim > 1:
                samples = samples.mean(axis=1)
            samples = _resample_linear(samples, sr, _SAMPLE_RATE)
            stream = self.recognizer.create_stream()
            stream.accept_waveform(_SAMPLE_RATE, samples)
            streams.append(stream)
        self.recognizer.decode_streams(streams)
        return [s.result.text.strip() for s in streams]

    # ── Full-file transcription (with VAD chunking) ──────────────────────

    def transcribe_file(self, audio_path: str) -> tuple[str, float]:
        """
        Load audio, chunk with VAD, transcribe all chunks, return (text, duration_s).
        Suitable for the /stt/ REST endpoint.
        """
        from src.services.chunk_audio import chunk_audio_file
        import asyncio

        samples, sr = sf.read(audio_path, dtype="float32")
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        duration = len(samples) / sr

        chunks = chunk_audio_file(audio_path)
        if not chunks:
            return "", duration

        # Use batch decode for all chunks
        texts = []
        for chunk in chunks:
            chunk_samples = _resample_linear(chunk.samples, chunk.sample_rate, _SAMPLE_RATE)
            stream = self.recognizer.create_stream()
            stream.accept_waveform(_SAMPLE_RATE, chunk_samples)
            self.recognizer.decode_stream(stream)
            t = stream.result.text.strip()
            if t:
                texts.append(t)

        transcript = " ".join(texts).capitalize()
        return transcript, duration

    # ── Diarization segment transcription ────────────────────────────────

    def transcribe_segments(
        self,
        audio_path: str,
        segments: list,
    ) -> list[dict]:
        """
        Transcribe each diarization segment.
        Returns: [{ "speaker_id": str, "start": float, "end": float, "text": str }]
        """
        samples, sr = sf.read(audio_path, dtype="float32")
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        samples = _resample_linear(samples, sr, _SAMPLE_RATE)
        sr = _SAMPLE_RATE

        turns = []
        os.makedirs("outputs/uploads", exist_ok=True)

        for seg in segments:
            s = max(0, int(seg.start * sr))
            e = min(len(samples), int(seg.end * sr))
            chunk = samples[s:e]
            if len(chunk) < sr * 0.1:
                continue

            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="outputs/uploads")
            tmp.close()
            try:
                sf.write(tmp.name, chunk, sr)
                text = self.transcribe_wav_sync(tmp.name)
            except Exception:
                text = ""
            finally:
                if os.path.exists(tmp.name):
                    os.remove(tmp.name)

            if text:
                turns.append({
                    "speaker_id": seg.speaker_id,
                    "start": seg.start,
                    "end": seg.end,
                    "text": text,
                })

        return turns


# ── Audio utilities ──────────────────────────────────────────────────────────


def _resample_linear(samples: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return samples
    ratio = sr_out / sr_in
    new_len = int(len(samples) * ratio)
    indices = np.linspace(0, len(samples) - 1, new_len)
    return np.interp(indices, np.arange(len(samples)), samples).astype(np.float32)


# ── Factory ──────────────────────────────────────────────────────────────────


def _determine_onnx_provider(provider_config: str) -> str:
    if provider_config == "cpu":
        logger.info("[Gipformer] Using CPUExecutionProvider (forced)")
        return "cpu"
    
    if provider_config == "cuda":
        if not _is_cuda_available():
            raise RuntimeError(
                "Config yêu cầu provider='cuda' nhưng CUDA không khả dụng. "
                "Hãy cài onnxruntime-gpu hoặc đổi provider sang 'auto' hoặc 'cpu'."
            )
        logger.info("[Gipformer] Using CUDAExecutionProvider (forced)")
        return "cuda"
    
    if provider_config == "tensorrt":
        if not _is_cuda_available():
            raise RuntimeError(
                "Config yêu cầu provider='tensorrt' nhưng CUDA không khả dụng. "
                "Hãy cài TensorRT + onnxruntime-gpu hoặc đổi provider sang 'auto' hoặc 'cpu'."
            )
        logger.info("[Gipformer] Using TensorRTExecutionProvider (forced)")
        return "tensorrt"
    
    # Auto mode: thử cuda trước, fallback về cpu
    if provider_config == "auto":
        if _is_cuda_available():
            logger.info("[Gipformer] Auto-selected CUDAExecutionProvider")
            return "cuda"
        else:
            logger.info("[Gipformer] Auto-selected CPUExecutionProvider (CUDA not available)")
            return "cpu"
    
    # Fallback mặc định
    logger.warning("[Gipformer] Unknown provider config '%s', defaulting to cpu", provider_config)
    return "cpu"


def _is_cuda_available() -> bool:
    """Kiểm tra xem CUDA có khả dụng cho ONNX Runtime không."""
    try:
        import onnxruntime as ort
        providers = ort.get_available_providers()
        return "CUDAExecutionProvider" in providers
    except ImportError:
        return False


def load_gipformer_engine(cfg: dict) -> GipformerEngine:
    """
    Load Gipformer ONNX model — ưu tiên dùng file cục bộ trong models/gipformer/.

    Luồng:
      1. Đọc local_model_path từ config (mặc định: models/gipformer)
      2. Kiểm tra file đã có chưa trong <local_model_path>/<quantize>/
      3. Nếu chưa → download từ HuggingFace Hub về đúng thư mục đó
      4. Load sherpa-onnx từ file cục bộ

    Args:
        cfg: Full app config (từ load_config()). Đọc cfg["gipformer"].
    """
    try:
        import sherpa_onnx
    except ImportError:
        raise RuntimeError("sherpa-onnx not installed. Run: pip install sherpa-onnx")

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        raise RuntimeError("huggingface_hub not installed. Run: pip install huggingface_hub>=0.20.0")

    gipformer_cfg: dict = cfg.get("gipformer", {})
    repo_id:           str   = gipformer_cfg.get("repo_id", "g-group-ai-lab/gipformer-65M-rnnt")
    quantize:          str   = gipformer_cfg.get("quantize", "int8")
    num_threads:       int   = int(gipformer_cfg.get("num_threads", 4))
    decoding_method:   str   = gipformer_cfg.get("decoding_method", "modified_beam_search")
    max_batch_size:    int   = int(gipformer_cfg.get("max_batch_size", 16))
    max_wait_ms:       float = float(gipformer_cfg.get("max_wait_ms", 100))
    local_model_path:  str   = gipformer_cfg.get(
        "local_model_path",
        r"models\gipformer",
    )

    if quantize not in _ONNX_FILES:
        raise ValueError(f"Invalid quantize: '{quantize}'. Must be 'fp32' or 'int8'.")

    # Thư mục chứa model theo từng quantize mode: .../gipformer/int8/ hoặc .../gipformer/fp32/
    quantize_dir = os.path.join(local_model_path, quantize)
    tokens_dir   = local_model_path  # tokens.txt dùng chung cho cả fp32 và int8
    os.makedirs(quantize_dir, exist_ok=True)
    os.makedirs(tokens_dir, exist_ok=True)

    # ── Tải hoặc xác nhận các file ONNX ─────────────────────────────────
    files_cfg = _ONNX_FILES[quantize]
    paths: dict[str, str] = {}

    for key, filename in files_cfg.items():
        local_path = os.path.join(quantize_dir, filename)
        if os.path.exists(local_path):
            logger.info("[Gipformer] Found local %s: %s", key, local_path)
            paths[key] = local_path
        else:
            logger.info("[Gipformer] Downloading %s (%s) → %s", filename, quantize.upper(), quantize_dir)
            paths[key] = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                local_dir=quantize_dir,
            )

    # tokens.txt dùng chung
    tokens_path = os.path.join(tokens_dir, "tokens.txt")
    if os.path.exists(tokens_path):
        logger.info("[Gipformer] Found local tokens.txt")
    else:
        logger.info("[Gipformer] Downloading tokens.txt → %s", tokens_dir)
        tokens_path = hf_hub_download(
            repo_id=repo_id,
            filename="tokens.txt",
            local_dir=tokens_dir,
        )
    paths["tokens"] = tokens_path

    # ── Xác định execution provider ─────────────────────────────────────
    provider_config = gipformer_cfg.get("provider", "auto")
    provider_str = _determine_onnx_provider(provider_config)
    
    logger.info("[Gipformer] All files ready. Loading recognizer (quantize=%s, provider=%s)...", 
                quantize, provider_str)

    recognizer = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=paths["encoder"],
        decoder=paths["decoder"],
        joiner=paths["joiner"],
        tokens=paths["tokens"],
        num_threads=num_threads,
        sample_rate=_SAMPLE_RATE,
        feature_dim=_FEATURE_DIM,
        decoding_method=decoding_method,
        provider=provider_str,
    )
    logger.info(
        "[Gipformer] ✓ Model loaded — quantize=%s, decoding=%s, threads=%d, provider=%s",
        quantize, decoding_method, num_threads, provider_str,
    )

    batching_engine = BatchingEngine(
        recognizer=recognizer,
        max_batch_size=max_batch_size,
        max_wait_ms=max_wait_ms,
    )

    return GipformerEngine(
        recognizer=recognizer,
        engine=batching_engine,
        quantize=quantize,
    )



# ── Backward-compat shim for diarization_service.py / conversation_workflow ─

class ASRService:
    """
    Thin shim giữ backward-compat với conversation_workflow.py → diarization_service.py.
    Delegates sang GipformerEngine singleton (set_engine tại startup).
    """

    def __init__(self, engine: "GipformerEngine | None" = None):
        self._engine = engine

    def _get_engine(self) -> "GipformerEngine":
        # Ưu tiên engine được truyền vào trực tiếp
        if self._engine is not None:
            return self._engine
        # Fallback: dùng module-level singleton (set tại startup trong main.py)
        return get_engine()

    def transcribe_segments(self, audio_path: str, segments: list) -> list[dict]:
        return self._get_engine().transcribe_segments(audio_path, segments)

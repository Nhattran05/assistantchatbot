"""
DiarizationService
------------------
Wraps the Sortformer diarization model (from demo.py) as a lazy-loaded
singleton so the heavy .nemo file is only loaded once per process.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache

import librosa
import soundfile as sf

# Default paths — can be overridden via config/app.yaml
_DEFAULT_MODEL_PATH = r"D:\diar_streaming_sortformer_4spk-v2\diar_streaming_sortformer_4spk-v2.nemo"

# High latency
_PRESET = dict(
    chunk_len=340,
    chunk_right_context=40,
    fifo_len=40,
    spkcache_update_period=300,
    spkcache_len=188,
)


@dataclass
class DiarSegment:
    start: float
    end: float
    speaker_id: str   # e.g. "speaker_0", "speaker_1"


@lru_cache(maxsize=1)
def _load_diar_model(model_path: str):
    from nemo.collections.asr.models import SortformerEncLabelModel
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if os.path.exists(model_path):
        model = SortformerEncLabelModel.restore_from(
            restore_path=model_path,
            map_location=device,
            strict=False,
        )
    else:
        model = SortformerEncLabelModel.from_pretrained(
            "nvidia/diar_streaming_sortformer_4spk-v2"
        )

    # Apply low-latency preset
    sm = model.sortformer_modules
    sm.chunk_len              = _PRESET["chunk_len"]
    sm.chunk_right_context    = _PRESET["chunk_right_context"]
    sm.fifo_len               = _PRESET["fifo_len"]
    sm.spkcache_update_period = _PRESET["spkcache_update_period"]
    sm.spkcache_len           = _PRESET["spkcache_len"]
    sm._check_streaming_parameters()

    model.eval()
    return model


def _parse_segment(seg) -> tuple[float, float, str]:
    if isinstance(seg, str):
        parts = seg.split()
        return float(parts[0]), float(parts[1]), parts[2]
    elif isinstance(seg, dict):
        start = float(seg.get("start", seg.get("begin", 0)))
        end   = float(seg.get("end", 0))
        spk   = str(seg.get("speaker", seg.get("label", "speaker_0")))
        return start, end, spk
    else:
        return float(seg[0]), float(seg[1]), str(seg[2])


def _preprocess_audio(audio_path: str) -> str:
    """Convert any audio to mono 16kHz WAV; return temp file path."""
    y, _ = librosa.load(audio_path, sr=16000, mono=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="outputs/uploads")
    tmp.close()  # Close handle immediately so Windows releases the lock
    sf.write(tmp.name, y, 16000)
    return tmp.name


class DiarizationService:
    def __init__(self, model_path: str | None = None):
        from src.utils import load_config
        cfg = load_config()
        self._model_path = (
            model_path
            or cfg.get("models", {}).get("diarization_path", _DEFAULT_MODEL_PATH)
        )

    def diarize(self, audio_path: str) -> list[DiarSegment]:
        """Run speaker diarization on a WAV file. Returns list of DiarSegment."""
        os.makedirs("outputs/uploads", exist_ok=True)
        ready_path = _preprocess_audio(audio_path)

        try:
            model = _load_diar_model(self._model_path)
            results = model.diarize(audio=ready_path, batch_size=1)
            segments: list[DiarSegment] = []
            for seg in results[0]:
                try:
                    start, end, spk = _parse_segment(seg)
                    segments.append(DiarSegment(start=start, end=end, speaker_id=spk))
                except Exception:
                    continue
            return segments
        finally:
            if os.path.exists(ready_path):
                os.remove(ready_path)

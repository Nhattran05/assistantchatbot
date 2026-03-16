"""
ASRService
----------
Wraps the Parakeet ASR model (from run.py) as a lazy-loaded singleton.
Transcribes individual audio segments cut from the original recording.
"""
from __future__ import annotations

import os
import tempfile
from functools import lru_cache

import librosa
import numpy as np
import soundfile as sf

_DEFAULT_MODEL_PATH = (
    r"C:\Users\kans\.cache\huggingface\hub"
    r"\models--nvidia--parakeet-ctc-0.6b-vi"
    r"\snapshots\b0493142b49458810324e3db8be9e8e07b4ebc17"
    r"\parakeet-ctc-0.6b-vi.nemo"
)

_TARGET_SR = 16_000


@lru_cache(maxsize=1)
def _load_asr_model(model_path: str):
    import nemo.collections.asr as nemo_asr
    return nemo_asr.models.ASRModel.restore_from(restore_path=model_path)


def _cut_segment(audio: np.ndarray, sr: int, start: float, end: float) -> np.ndarray:
    s = max(0, int(start * sr))
    e = min(len(audio), int(end * sr))
    return audio[s:e]


class ASRService:
    def __init__(self, model_path: str | None = None):
        from src.utils import load_config
        cfg = load_config()
        self._model_path = (
            model_path
            or cfg.get("models", {}).get("asr_path", _DEFAULT_MODEL_PATH)
        )

    def transcribe_segments(
        self,
        audio_path: str,
        segments: list,   # list[DiarSegment]
    ) -> list[dict]:
        """
        For each DiarSegment, cut the audio and transcribe.

        Returns list of dicts:
          { "speaker_id": str, "start": float, "end": float, "text": str }
        """
        audio, sr = librosa.load(audio_path, sr=_TARGET_SR, mono=True)
        model = _load_asr_model(self._model_path)

        os.makedirs("outputs/uploads", exist_ok=True)
        turns = []

        for seg in segments:
            chunk = _cut_segment(audio, sr, seg.start, seg.end)
            if len(chunk) < sr * 0.1:
                # Skip segments shorter than 100ms — likely noise
                continue

            tmp = tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, dir="outputs/uploads"
            )
            tmp.close()  # Close handle immediately so Windows releases the lock
            try:
                sf.write(tmp.name, chunk, sr)
                result = model.transcribe([tmp.name])
                text = result[0].text if hasattr(result[0], "text") else str(result[0])
                text = text.strip()
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

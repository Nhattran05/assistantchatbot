from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

import librosa
import soundfile as sf
import nemo.collections.asr as nemo_asr

# Filled from current sample code (src/services/asr_service.py)
MODEL_PATH = (
    r"C:\Users\kans\.cache\huggingface\hub"
    r"\models--nvidia--parakeet-ctc-0.6b-vi"
    r"\snapshots\b0493142b49458810324e3db8be9e8e07b4ebc17"
    r"\parakeet-ctc-0.6b-vi.nemo"
)

# You can change this path to your own sample file.
AUDIO_PATH = r"D:\nvidia parakeet\sample3.WAV"


def get_audio_duration_seconds(audio_path: str) -> float:
    info = sf.info(audio_path)
    return float(info.frames) / float(info.samplerate)


def preprocess_to_mono_16k_wav(audio_path: str) -> str:
    """Convert any audio file to a mono 16k WAV and return temp file path."""
    os.makedirs(r"D:\nvidia parakeet\outputs\uploads", exist_ok=True)
    y, _ = librosa.load(audio_path, sr=16000, mono=True)
    tmp = tempfile.NamedTemporaryFile(
        suffix=".wav", delete=False, dir=r"D:\nvidia parakeet\outputs\uploads"
    )
    tmp.close()  # Release lock on Windows before writing.
    sf.write(tmp.name, y, 16000)
    return tmp.name


def main() -> None:
    model_file = Path(MODEL_PATH)
    audio_file = Path(AUDIO_PATH)

    if not model_file.exists():
        raise FileNotFoundError(f"Model file not found: {model_file}")
    if not audio_file.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    model = nemo_asr.models.ASRModel.restore_from(restore_path=str(model_file))

    audio_duration = get_audio_duration_seconds(str(audio_file))
    if audio_duration <= 0:
        raise ValueError("Audio duration must be greater than 0 seconds.")

    # Timing starts at the beginning of processing (preprocess + transcribe).
    t0 = time.perf_counter()
    ready_wav = preprocess_to_mono_16k_wav(str(audio_file))
    try:
        result = model.transcribe([ready_wav])
    finally:
        try:
            if os.path.exists(ready_wav):
                os.remove(ready_wav)
        except OSError:
            # Ignore cleanup failure on Windows if file is still being released.
            pass
    t1 = time.perf_counter()

    processing_time = t1 - t0
    rtf = processing_time / audio_duration

    transcript = result[0].text if hasattr(result[0], "text") else str(result[0])

    print("=== Parakeet RTF Benchmark ===")
    print(f"Model path      : {model_file}")
    print(f"Audio path      : {audio_file}")
    print(f"Audio duration  : {audio_duration:.3f} s")
    print(f"Processing time : {processing_time:.3f} s")
    print(f"RTF             : {rtf:.4f}")
    print("\n=== Transcript ===")
    print(transcript.strip())


if __name__ == "__main__":
    main()

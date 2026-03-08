import librosa
import soundfile as sf
import os
import nemo.collections.asr as nemo_asr

def preprocess_audio(audio_path):
    target_sr = 16000
    y, sr = librosa.load(audio_path, sr=target_sr, mono=True)
    processed_path = r'D:\nvidia parakeet\temp_mono_16k.wav'
    sf.write(processed_path, y, target_sr)
    return processed_path

model_path = r'C:\Users\kans\.cache\huggingface\hub\models--nvidia--parakeet-ctc-0.6b-vi\snapshots\b0493142b49458810324e3db8be9e8e07b4ebc17\parakeet-ctc-0.6b-vi.nemo'
asr_model = nemo_asr.models.ASRModel.restore_from(restore_path=model_path)

raw_audio = r'D:\nvidia parakeet\sample_10.wav'
ready_audio = preprocess_audio(raw_audio)

transcriptions = asr_model.transcribe([ready_audio])
print(f"Kết quả: {transcriptions[0].text}")

if os.path.exists(ready_audio):
    os.remove(ready_audio)


# Quick Start Guide - Gipformer Migration

## Tổng Quan Thay Đổi

Project đã được chuyển từ **NVIDIA Parakeet** sang **Gipformer 65M RNNT** để xử lý Speech-to-Text.

### Lợi Ích Chính
- ✅ Model tự động tải về lần đầu khởi động
- ✅ Hoạt động offline sau khi tải xong
- ✅ Hỗ trợ cả CPU và GPU
- ✅ Độ trễ thấp hơn, streaming-capable
- ✅ Dependencies nhẹ hơn (không cần NeMo ASR cho STT)

## Cài Đặt Nhanh

### Bước 1: Cài Dependencies
```bash
pip install -r requirements.txt
```

### Bước 2: Tải Model Diarization (Thủ công)
```bash
# Windows PowerShell
wget https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2/resolve/main/diar_streaming_sortformer_4spk-v2.nemo `
     -OutFile "models\diarization\diar_streaming_sortformer_4spk-v2.nemo"
```

### Bước 3: Khởi Động Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Lưu ý**: Lần đầu khởi động, Gipformer model sẽ tự động tải về (~100MB). Chờ khoảng 1-2 phút.

## Cấu Hình

### File: config/app.yaml

```yaml
# Gipformer ASR Configuration
gipformer:
  quantize: "fp32"        # "fp32" (chính xác) hoặc "int8" (nhanh hơn)
  provider: "auto"        # "auto", "cuda" (GPU), hoặc "cpu"
  num_threads: 4          # Số threads cho CPU inference

# Diarization Model
models:
  diarization_path: "models\\diarization\\diar_streaming_sortformer_4spk-v2.nemo"
  device: "auto"          # "auto", "cuda", hoặc "cpu"

# Voice Activity Detection
silero_vad:
  threshold: 0.4
  min_silence_duration_ms: 500
```

## Kiểm Tra GPU

### Check CUDA Support
```python
# ONNX Runtime
import onnxruntime as ort
print("ONNX Providers:", ort.get_available_providers())

# PyTorch (cho diarization)
import torch
print("PyTorch CUDA:", torch.cuda.is_available())
```

### Kích Hoạt GPU
1. Cài CUDA Toolkit 11.8 hoặc 12.x
2. Cài GPU packages:
```bash
pip install onnxruntime-gpu>=1.16.1
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## API Endpoints (Không Đổi)

### 1. Phân Tích Cuộc Hội Thoại
```bash
POST /conversation/analyze
Content-Type: multipart/form-data

file: <audio_file.wav>
```

Response:
```json
{
  "filled_form": {
    "full_name": "...",
    "phone_number": "...",
    ...
  },
  "docx_path": "outputs/..."
}
```

### 2. Tải File DOCX
```bash
GET /conversation/download?path=outputs/...
```

### 3. Health Check
```bash
GET /health
```

## Troubleshooting

### 1. Model Không Tải
**Lỗi**: Cannot download from HuggingFace
**Giải pháp**:
- Kiểm tra kết nối Internet
- Thử tải thủ công từ https://huggingface.co/g-group-ai-lab/gipformer-65M-rnnt

### 2. GPU Không Nhận Diện
**Lỗi**: CUDA provider NOT available
**Giải pháp**:
```bash
pip uninstall onnxruntime
pip install onnxruntime-gpu
```

### 3. Diarization Model Không Tìm Thấy
**Lỗi**: Diarization model not found
**Giải pháp**: Tải file .nemo thủ công (xem Bước 2 ở trên)

### 4. Lỗi Import
**Lỗi**: ModuleNotFoundError: No module named 'sherpa_onnx'
**Giải pháp**:
```bash
pip install sherpa-onnx
```

## Cấu Trúc Thư Mục

```
assistantchatbot/
├── models/
│   ├── gipformer/          # Tự động tải
│   │   ├── tokens.txt
│   │   ├── fp32/           # Model độ chính xác cao
│   │   └── int8/           # Model đã quantize (nhanh hơn)
│   └── diarization/        # Tải thủ công
│       └── diar_streaming_sortformer_4spk-v2.nemo
├── src/
│   ├── services/
│   │   ├── asr_service.py       # ✓ Đã update (Gipformer)
│   │   ├── chunk_audio.py       # ✓ Mới (VAD chunking)
│   │   └── diarization_service.py # ✓ Đã update (device config)
│   ├── routers/                 # Không đổi
│   └── core/                    # Không đổi
├── config/
│   └── app.yaml                 # ✓ Đã update (Gipformer config)
├── main.py                      # ✓ Đã update (lifespan init)
├── requirements.txt             # ✓ Đã update (dependencies)
└── MIGRATION_TO_GIPFORMER.md    # ✓ Mới (tài liệu chi tiết)
```

## Performance

| Mode | Speed | Accuracy | Requirements |
|------|-------|----------|--------------|
| CPU (fp32) | ~2-3x slower | Cao nhất | Chỉ cần CPU |
| CPU (int8) | ~2x slower | Rất tốt | Chỉ cần CPU |
| GPU (fp32) | Nhanh | Cao nhất | CUDA GPU |
| GPU (int8) | Nhanh nhất | Rất tốt | CUDA GPU |

**Khuyến nghị**: 
- Development/Testing: CPU với `quantize: "int8"`
- Production: GPU với `quantize: "fp32"`

## Code Không Đổi

Tất cả code hiện tại vẫn hoạt động bình thường:
- ✅ Routers (`src/routers/*.py`)
- ✅ Agents (`src/core/agents/*.py`)
- ✅ Workflows (`src/core/workflows/*.py`)
- ✅ Frontend code

Interface `ASRService` giữ nguyên:
```python
from src.services.asr_service import ASRService

asr = ASRService()
turns = asr.transcribe_segments(audio_path, segments)
```

## Kiểm Tra Hoạt Động

### Test 1: Health Check
```bash
curl http://localhost:8000/health
```
Expected: `{"status":"ok"}`

### Test 2: Conversation Analysis
```bash
curl -X POST http://localhost:8000/conversation/analyze \
  -F "file=@test_audio.wav"
```

### Test 3: Check Logs
Server khởi động sẽ hiển thị:
```
[Startup] Loading Gipformer engine...
[Gipformer] Downloading encoder...
[Gipformer] ✓ Model loaded — quantize=fp32, provider=cuda
[Startup] ✓ Gipformer engine ready
[Startup] ✓ Silero VAD preloaded
[Startup] ✓ Diarization model preloaded
SERVER READY - Running on GPU
```

## Liên Hệ & Support

- Migration guide đầy đủ: `MIGRATION_TO_GIPFORMER.md`
- Reference project: `D:\nvidia parakeet\`
- Logs: Kiểm tra console output khi server khởi động

---

**Lưu ý quan trọng**: 
1. Lần đầu khởi động cần Internet để tải Gipformer model
2. Các lần sau hoạt động hoàn toàn offline
3. File diarization model cần tải thủ công (1 lần duy nhất)

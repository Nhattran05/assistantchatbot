# Gipformer STT & Multi-Agent Conversation System

Dự án này là hệ thống tích hợp API FastAPI cho quá trình Speech-to-Text (chuyển đổi giọng nói thành văn bản) và hệ thống Multi-Agent xử lý logic hội thoại (như xác định role, chuẩn hóa văn bản, điền form, tạo tài liệu v.v.).

Dự án sử dụng:
- **ASR Engine**: Gipformer 65M RNNT (thông qua `sherpa-onnx`) cho streaming STT tốc độ cao, độ trễ thấp.
- **VAD**: Silero VAD (ONNX) để phát hiện giọng nói.
- **Diarization**: NeMo (`diar_streaming_sortformer_4spk-v2`) để nhận diện người nói.
- **Framework & AI**: FastAPI, LangChain, LangGraph.

---

## 🚀 1. Yêu cầu hệ thống

- Hệ điều hành: Windows / Linux / macOS
- Python: **3.11+**
- Git

---

## 🛠 2. Hướng dẫn cài đặt

### Bước 1: Clone dự án
```bash
git clone <url-repo-cua-ban>
cd assistantchatbot
```

### Bước 2: Tạo và kích hoạt môi trường ảo (Virtual Environment)
Khuyến nghị sử dụng môi trường ảo để tránh xung đột thư viện.

**Trên Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Trên Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Bước 3: Cài đặt Dependencies
Cài đặt toàn bộ thư viện cần thiết thông qua `requirements.txt`:
```bash
pip install -r requirements.txt
```

*(Lưu ý: Dự án phụ thuộc vào `sherpa-onnx`, `silero-vad`, `torch`, `torchaudio`, `nemo_toolkit[asr]`.)*

---

## 📥 3. Cài đặt Model

### 3.1. Gipformer ASR (Tự động)
Model **Gipformer 65M RNNT** (dùng cho chuyển giọng nói → văn bản) sẽ được **tự động tải về** khi bạn khởi động server lần đầu tiên.

Model được lưu vào thư mục dự án tại:
```
models/
└── gipformer/
    ├── tokens.txt
    ├── int8/          ← encoder, decoder, joiner (.int8.onnx)  – mặc định
    └── fp32/          ← encoder, decoder, joiner (.onnx)        – chọn trong app.yaml
```

Bạn có thể đổi chế độ lượng tử hóa (mặc định là `fp32`) tại `config/app.yaml`:
```yaml
gipformer:
  quantize: "fp32"   # hoặc "int8" để tăng tốc độ
```

> **Lưu ý:** Lần đầu khởi động cần kết nối Internet để tải model (~100MB). Các lần sau hoàn toàn offline.

### 3.2. Diarization (Tải thủ công)

Dự án sử dụng model **Diarization Streaming Sortformer** của NVIDIA.
Bạn cần tải file `.nemo` và đặt vào **đúng thư mục** trong dự án.

**Link Model:** [nvidia/diar_streaming_sortformer_4spk-v2](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2)

**Các bước thực hiện:**
1. Truy cập tab **[Files and versions](https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2/tree/main)**.
2. Tải file: `diar_streaming_sortformer_4spk-v2.nemo` (~450MB).
3. Copy file vào thư mục sau trong dự án:

```
models/
└── diarization/
    └── diar_streaming_sortformer_4spk-v2.nemo  ← đặt file vào đây
```

```bash
# Tải trực tiếp vào đúng thư mục (Windows PowerShell)
wget https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2/resolve/main/diar_streaming_sortformer_4spk-v2.nemo `
     -OutFile "models\diarization\diar_streaming_sortformer_4spk-v2.nemo"

# Linux / macOS
wget -P models/diarization https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2/resolve/main/diar_streaming_sortformer_4spk-v2.nemo
```

---

## ⚙️ 4. Cấu hình biến môi trường

Dự án cần một số API Keys (đặc biệt là cho hệ thống LLM / Agents).

1. Copy file template cấu hình:
    - **Windows:** `copy .env.example .env`
    - **Linux/Mac:** `cp .env.example .env`
2. Mở file `.env` bằng Editor và điền các API keys cần thiết, ví dụ:
   ```env
   MEGALLM_API_KEY=sk-...
   OPENAI_API_KEY=sk-...
   PORT=8000
   APP_ENV=development
   ```

*Lưu ý: Bạn có thể tham khảo/sửa cấu hình mặc định (Provider, Model) cho các Agent tại file `config/app.yaml`.*

---

## 🚀 5. Khởi chạy hệ thống

Khi tất cả đã sẵn sàng, bạn có thể khởi động server FastAPI.

**Chạy trực tiếp qua Uvicorn**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Sau khi khởi chạy thành công:
- **API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🎮 6. Chạy Voice Agent (LiveKit)

Để chạy voice call agent với LiveKit, cần khởi động thêm một service:

```bash
python src/livekit_app.py dev
```

Sau đó, khởi động frontend:
```bash
cd frontend
npm install
npm run dev
```

Truy cập: [http://localhost:3000](http://localhost:3000)

---

## 📁 7. Cấu trúc thư mục

```
assistantchatbot/
├── config/
│   └── app.yaml              # Cấu hình chính: LLM, Agent, Gipformer, VAD
├── models/                   # Toàn bộ model weights lưu tại đây
│   ├── diarization/
│   │   └── diar_streaming_sortformer_4spk-v2.nemo   # Tải thủ công
│   └── gipformer/
│       ├── tokens.txt                               # Tự động tải khi startup
│       ├── int8/                                    # Model lượng tử hóa int8
│       │   ├── encoder-epoch-35-avg-6.int8.onnx
│       │   ├── decoder-epoch-35-avg-6.int8.onnx
│       │   └── joiner-epoch-35-avg-6.int8.onnx
│       └── fp32/                                    # Model độ chính xác cao (mặc định)
│           ├── encoder-epoch-35-avg-6.onnx
│           ├── decoder-epoch-35-avg-6.onnx
│           └── joiner-epoch-35-avg-6.onnx
├── src/
│   ├── core/
│   │   ├── agents/           # Các Agent xử lý logic (RoleIdentifier, TextNormalizer, FormFiller...)
│   │   ├── workflows/        # LangGraph Workflow definitions
│   │   ├── llm/              # LLM Factory (OpenAI, MegaLLM...)
│   │   └── prompts/          # System prompts cho từng Agent (.md)
│   ├── routers/              # FastAPI Routers (conversation, voice_call...)
│   ├── services/             # Core services (ASR, Diarization, Chunking, VAD)
│   ├── databases/            # Database layer
│   ├── utils/                # Utilities & helpers
│   └── livekit_app.py        # LiveKit agent server
├── agent-starter-react/      # React frontend for voice agent
├── docs/                      # Documentation
├── main.py                    # Entry point — FastAPI app + lifespan
├── requirements.txt           # Python dependencies
├── .env                       # API Keys (tạo từ .env.example)
├── MIGRATION_TO_GIPFORMER.md  # Migration guide
├── QUICK_START_GIPFORMER.md   # Quick start guide (Vietnamese)
└── MIGRATION_CHECKLIST.md     # Testing checklist
```

---

## 📚 8. Tài liệu tham khảo

- **QUICK_START_GIPFORMER.md** - Hướng dẫn nhanh (tiếng Việt) 🇻🇳
- **MIGRATION_TO_GIPFORMER.md** - Chi tiết quá trình migration từ Parakeet
- **MIGRATION_CHECKLIST.md** - Checklist cài đặt và kiểm tra
- **docs/** - Thêm tài liệu chi tiết khác

Để hiểu chi tiết về cách tạo Agent, Tool, và Workflow mới, xem tài liệu trong thư mục `docs/`.

---

## ⚡ 9. Performance & GPU Support

### Quantization Options
- **fp32** (mặc định): Chính xác cao nhất (~1x tốc độ GPU)
- **int8**: Nhanh 30% hơn với độ chính xác vẫn rất tốt

### GPU Support
Để bật GPU acceleration:

1. Cài CUDA Toolkit (11.8 hoặc 12.x)
2. Cài GPU packages:
```bash
pip install onnxruntime-gpu>=1.16.1
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

3. Hệ thống sẽ **tự động detect GPU** và sử dụng nó.

---

## 🐛 Troubleshooting

### Model không tải
- Kiểm tra kết nối Internet (lần đầu cần tải)
- Kiểm tra quyền ghi vào thư mục `models/`
- Tải thủ công từ HuggingFace Hub

### GPU không được detect
```bash
python -c "import onnxruntime as ort; print(ort.get_available_providers())"
```
Nếu không thấy `CUDAExecutionProvider`, cài lại `onnxruntime-gpu`.

### Import error
```bash
pip install sherpa-onnx
pip install silero-vad
```

---

## 🎯 Next Steps

1. **Cài dependencies**: `pip install -r requirements.txt`
2. **Tải diarization model** (xem phần 3.2)
3. **Khởi động server**: `uvicorn main:app --reload`
4. **Gipformer tự động tải** lần đầu khởi động
5. **Test API**: Truy cập http://localhost:8000/docs

---

**Chúc bạn cài đặt thành công!** 🚀

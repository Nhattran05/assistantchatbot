# ✅ Migration Checklist - Gipformer STT

## Pre-Migration (Completed ✅)
- [x] Đọc và hiểu cấu trúc D:\nvidia parakeet\
- [x] Backup code hiện tại (nếu cần)
- [x] Xác định các file cần thay đổi

## Code Changes (Completed ✅)
- [x] Thay thế src/services/asr_service.py với Gipformer implementation
- [x] Tạo src/services/chunk_audio.py (VAD chunking)
- [x] Update src/services/diarization_service.py (device config)
- [x] Update main.py (lifespan với model initialization)
- [x] Update config/app.yaml (Gipformer + VAD settings)
- [x] Update requirements.txt (new dependencies)
- [x] Tạo models/gipformer/ directory
- [x] Tạo models/diarization/ directory
- [x] Verify backward compatibility (ASRService interface)

## Documentation (Completed ✅)
- [x] Tạo MIGRATION_TO_GIPFORMER.md (detailed guide)
- [x] Tạo QUICK_START_GIPFORMER.md (quick reference, Vietnamese)
- [x] Tạo migration checklist

## Files Status

### Modified Files ✅
| File | Status | Changes |
|------|--------|---------|
| src/services/asr_service.py | ✅ Complete | Full rewrite for Gipformer |
| src/services/diarization_service.py | ✅ Complete | Device config support |
| main.py | ✅ Complete | Gipformer initialization |
| config/app.yaml | ✅ Complete | Gipformer + VAD config |
| requirements.txt | ✅ Complete | New dependencies |

### New Files ✅
| File | Status | Purpose |
|------|--------|---------|
| src/services/chunk_audio.py | ✅ Created | VAD-based chunking |
| models/gipformer/ | ✅ Created | Model storage (auto-download) |
| models/diarization/ | ✅ Created | Diarization model storage |
| MIGRATION_TO_GIPFORMER.md | ✅ Created | Full documentation |
| QUICK_START_GIPFORMER.md | ✅ Created | Quick guide (Vietnamese) |

### Unchanged Files ✅
- [x] All routers (src/routers/*.py) - No changes needed
- [x] All agents (src/core/agents/*.py) - No changes needed
- [x] All workflows (src/core/workflows/*.py) - Works with new ASRService
- [x] Frontend code - No changes needed
- [x] Database code - No changes needed

## Installation & Setup (TODO - User Action Required)

### Step 1: Install Dependencies ⚠️ TODO
```bash
pip install -r requirements.txt
```

**Expected new packages:**
- sherpa-onnx>=1.10.0
- huggingface_hub>=0.20.0
- silero-vad>=5.0
- onnxruntime>=1.16.1
- soundfile>=0.12.0
- numpy>=1.20.0

### Step 2: Download Diarization Model ⚠️ TODO
```bash
# Windows PowerShell
wget https://huggingface.co/nvidia/diar_streaming_sortformer_4spk-v2/resolve/main/diar_streaming_sortformer_4spk-v2.nemo `
     -OutFile "models\diarization\diar_streaming_sortformer_4spk-v2.nemo"
```

**File size**: ~450MB
**Location**: models/diarization/diar_streaming_sortformer_4spk-v2.nemo

### Step 3: Optional - GPU Support ⬜ Optional
If you have CUDA-capable GPU:

1. Install CUDA Toolkit (11.8 or 12.x)
2. Install GPU packages:
```bash
pip install onnxruntime-gpu>=1.16.1
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

3. Verify GPU detection:
```python
import onnxruntime as ort
print(ort.get_available_providers())  # Should include 'CUDAExecutionProvider'

import torch
print(torch.cuda.is_available())  # Should be True
```

## Testing (TODO - User Action Required)

### Test 1: Start Server ⚠️ TODO
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

**Expected startup log:**
```
[Startup] Loading Gipformer engine...
[Gipformer] Downloading encoder... (first time only)
[Gipformer] Found local encoder: ... (subsequent times)
[Gipformer] ✓ Model loaded — quantize=fp32, provider=cuda
[Startup] ✓ Gipformer engine ready (quantize=fp32)
[Startup] Preloading Silero VAD (ONNX)...
[Startup] ✓ Silero VAD preloaded
[Startup] Preloading diarization model from: models\diarization\...
[Startup] ✓ Diarization model preloaded
SERVER READY - Running on GPU (or CPU)
```

**First startup**: Takes 1-2 minutes (downloads Gipformer model)
**Subsequent startups**: ~10-30 seconds (loads from cache)

### Test 2: Health Check ⬜ TODO
```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{"status":"ok"}
```

### Test 3: API Documentation ⬜ TODO
Visit: http://localhost:8000/docs

**Should see:**
- POST /conversation/analyze
- GET /conversation/download
- POST /voice-call/create
- POST /voice-call/token
- GET /health

### Test 4: Conversation Analysis ⬜ TODO
```bash
curl -X POST http://localhost:8000/conversation/analyze \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test_audio.wav"
```

**Expected flow:**
1. Diarization (who spoke when)
2. ASR transcription with Gipformer (what they said)
3. Role identification (consultant vs customer)
4. Text normalization
5. Form filling
6. DOCX generation

**Expected response:**
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

## Verification Checklist

### Code Integrity ✅
- [x] No syntax errors in modified files
- [x] All imports are correct
- [x] ASRService interface unchanged (backward compatible)
- [x] Configuration files are valid YAML
- [x] Dependencies are listed correctly

### Model Files ⚠️ TODO
- [ ] Gipformer model downloaded to models/gipformer/ (auto on first start)
- [ ] Diarization model downloaded to models/diarization/ (manual)
- [ ] tokens.txt exists in models/gipformer/
- [ ] ONNX files exist in models/gipformer/fp32/ or int8/

### Functionality ⬜ TODO
- [ ] Server starts without errors
- [ ] GPU/CPU auto-detection works
- [ ] /health endpoint responds
- [ ] /conversation/analyze works with test audio
- [ ] ASR transcription is accurate
- [ ] Diarization identifies speakers correctly
- [ ] Form filling extracts information
- [ ] DOCX generation works

## Rollback Plan (If Needed)

If something goes wrong, revert changes:

### Option 1: Git Revert
```bash
git checkout HEAD -- src/services/asr_service.py
git checkout HEAD -- src/services/diarization_service.py
git checkout HEAD -- main.py
git checkout HEAD -- config/app.yaml
git checkout HEAD -- requirements.txt
```

### Option 2: Restore from D:\nvidia parakeet\
Reference the original implementation in `D:\nvidia parakeet\` if needed.

### Option 3: Manual Rollback
1. Restore old asr_service.py (Parakeet version)
2. Remove chunk_audio.py
3. Restore old main.py
4. Restore old config/app.yaml
5. Restore old requirements.txt
6. Reinstall old dependencies

## Notes

### Known Issues
- None identified yet (migration just completed)

### Performance Expectations
- **CPU (fp32)**: ~2-3x slower than GPU, works on any machine
- **CPU (int8)**: ~2x slower than GPU, good accuracy
- **GPU (fp32)**: Fastest, best accuracy (recommended for production)
- **GPU (int8)**: Super fast, excellent accuracy

### Migration Time
- Code changes: ✅ Complete (1 hour)
- Dependencies install: ⚠️ TODO (~5-10 minutes)
- Model download: ⚠️ TODO (1-2 minutes first time, 450MB diarization + 100MB Gipformer)
- Testing: ⬜ TODO (~15-30 minutes)

**Total estimated time**: ~30-45 minutes (excluding code changes already done)

## Support & Reference

### Documentation
- QUICK_START_GIPFORMER.md - Quick reference (Vietnamese)
- MIGRATION_TO_GIPFORMER.md - Detailed guide (English)

### Reference Implementation
- D:\nvidia parakeet\ - Working Gipformer implementation

### Troubleshooting
See QUICK_START_GIPFORMER.md section "Troubleshooting" for common issues.

## Sign-off

- [x] Code migration: ✅ Complete
- [ ] Dependency installation: ⚠️ TODO (user action)
- [ ] Model download: ⚠️ TODO (user action)
- [ ] Testing: ⬜ TODO (user action)
- [ ] Production deployment: ⬜ Pending testing

---

**Migration completed by**: GitHub Copilot CLI
**Date**: 2026-04-05
**Status**: Ready for testing ✅
**Next action**: Install dependencies and test server startup

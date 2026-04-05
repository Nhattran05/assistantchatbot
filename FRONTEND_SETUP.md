# Frontend Setup - agent-starter-react

## ✅ Setup Complete

The new React frontend (`agent-starter-react`) is now connected to your backend!

## Configuration

### Frontend (.env.local)
- **Location**: `D:\assistantchatbot\agent-starter-react\.env.local`
- **LiveKit URL**: wss://callbot-ai-r4dyt43t.livekit.cloud
- **Agent Name**: data-collection-agent
- **Backend URL**: http://localhost:8000

### Backend (.env)
- **Location**: `D:\assistantchatbot\.env`
- **FastAPI Port**: 8000
- **LiveKit credentials**: Configured ✓

## How to Start

### Quick Start (All Services)
```bash
start-all.bat
```

This will start:
1. **Backend** - FastAPI on port 8000
2. **LiveKit Agent** - Running on port 7860
3. **Frontend** - Next.js on port 3000

### Individual Services

**Backend Only:**
```bash
uvicorn main:app --reload --port 8000
```

**Agent Only:**
```bash
python src\livekit_app.py dev
```

**Frontend Only:**
```bash
cd agent-starter-react
npm run dev
```

## Access Points

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Features

- ✅ LiveKit voice agent integration
- ✅ Token generation via Next.js API route
- ✅ Backend API connection ready
- ✅ Data collection agent configured

## Old Frontend

The old `frontend` folder has been **deleted** ✓

## Next Steps

1. Run `start-all.bat` to start all services
2. Wait 5-10 seconds for services to initialize
3. Open http://localhost:3000
4. Click "Start call" to test the voice agent!

---

*Setup completed on 2026-04-04*

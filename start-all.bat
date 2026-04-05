@echo off
REM ==================================================
REM Quick Start - LiveKit Voice Agent
REM ==================================================
REM This script starts all 3 required services

echo.
echo ========================================
echo LiveKit Voice Agent - Quick Start
echo ========================================
echo.
echo Starting 3 services:
echo 1. FastAPI Backend (port 8000)
echo 2. LiveKit Agent Server
echo 3. Next.js Frontend (port 3000)
echo.
echo Press Ctrl+C in each window to stop
echo ========================================
echo.

REM Start Backend
echo Starting Backend...
start "Backend - FastAPI" cmd /k "cd /d D:\assistantchatbot && uvicorn main:app --reload --port 8000"
timeout /t 2 /nobreak >nul

REM Start Agent
echo Starting Agent...
start "Agent - LiveKit" cmd /k "cd /d D:\assistantchatbot && python src\livekit_app.py dev"
timeout /t 2 /nobreak >nul

REM Start Frontend
echo Starting Frontend...
start "Frontend - Next.js" cmd /k "cd /d D:\assistantchatbot\agent-starter-react && npm run dev"
timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo 3 windows opened:
echo - Backend: http://localhost:8000
echo - Agent: Running on port 7860
echo - Frontend: http://localhost:3000
echo.
echo Wait 5-10 seconds, then open:
echo.
echo   http://localhost:3000
echo.
echo Click "Bắt đầu cuộc gọi" to test!
echo ========================================
echo.
timeout /t 3
start http://localhost:3000

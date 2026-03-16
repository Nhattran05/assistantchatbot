@echo off
REM ============================================================
REM  run_demo.bat — Setup & run Streaming Sortformer demo
REM  Usage:
REM    run_demo.bat                  (download sample, low latency)
REM    run_demo.bat my_audio.wav     (custom audio, low latency)
REM    run_demo.bat my_audio.wav high_latency
REM ============================================================

setlocal

REM --- Resolve script directory ---
set "SCRIPT_DIR=%~dp0"
set "MODEL_PATH=%SCRIPT_DIR%diar_streaming_sortformer_4spk-v2.nemo"

REM --- Check Python ---
where python >nul 2>&1
if errorlevel 1 (
    echo [error] python not found in PATH. Please install Python 3.10+.
    pause & exit /b 1
)

REM --- Check if NeMo is installed ---
python -c "import nemo" >nul 2>&1
if errorlevel 1 (
    echo [info] NeMo not found. Installing dependencies...
    echo.

    REM Install Cython + packaging first
    pip install Cython packaging
    if errorlevel 1 ( echo [error] Failed to install Cython/packaging. & pause & exit /b 1 )

    REM Install NeMo ASR from GitHub
    pip install "git+https://github.com/NVIDIA/NeMo.git@main#egg=nemo_toolkit[asr]"
    if errorlevel 1 ( echo [error] Failed to install NeMo. & pause & exit /b 1 )

    REM Install remaining requirements
    pip install -r "%SCRIPT_DIR%requirements.txt"
    if errorlevel 1 ( echo [error] Failed to install requirements. & pause & exit /b 1 )

    echo [info] All dependencies installed successfully.
    echo.
) else (
    echo [info] NeMo is already installed.
)

REM --- Build the python command ---
set "AUDIO_ARG="
set "PRESET_ARG=--preset low_latency"

if not "%~1"=="" (
    set "AUDIO_ARG=--audio %~1"
)
if not "%~2"=="" (
    set "PRESET_ARG=--preset %~2"
)

echo [info] Running demo...
echo.
python "%SCRIPT_DIR%demo.py" %AUDIO_ARG% %PRESET_ARG%

echo.
pause

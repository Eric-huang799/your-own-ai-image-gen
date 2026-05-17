@echo off
chcp 65001 >nul 2>&1
title 你自己的AI生图 - AI Image Studio

echo ===========================================
echo    你自己的AI生图 - 本地AI图像生成工作室
echo ===========================================
echo.

:: Check Python
echo [Check] Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

:: Check deps
echo [Check] Python deps...
python -c "import PIL, requests, tkinter" >nul 2>&1
if errorlevel 1 (
    echo [Install] Installing deps...
    python -m pip install -r requirements.txt -q
)

:: Check Ollama
echo [Check] Ollama...
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=2)" >nul 2>&1
if errorlevel 1 (
    echo [Start] Starting Ollama...
    start "Ollama" ollama serve
    echo [Wait] Waiting for Ollama...
    timeout /t 5 /nobreak >nul
) else (
    echo [OK] Ollama running
)

:: Check ComfyUI
echo [Check] ComfyUI...
set COMFY_OK=0
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8188/system_stats', timeout=2)" >nul 2>&1 && set COMFY_OK=1
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8189/system_stats', timeout=2)" >nul 2>&1 && set COMFY_OK=1
if %COMFY_OK%==0 (
    echo.
    echo [Warning] ComfyUI not detected on port 8188 or 8189.
    echo You can start it manually, or the app will try to auto-start it.
    echo Make sure ComfyUI is installed at ~/ComfyUI/main.py
    echo.
) else (
    echo [OK] ComfyUI running
)

:: Launch
echo.
echo ===========================================
echo    Launching AI Image Studio...
echo ===========================================
python "%~dp0ai_image_studio.py"
pause

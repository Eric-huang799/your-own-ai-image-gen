@echo off
chcp 65001 >nul 2>&1
title AI Image Studio

echo ===========================================
echo   AI Image Studio - v3.2
echo   1. 桌面 GUI 版 (tkinter)
echo   2. 网页 WebUI 版 (浏览器)
echo ===========================================
echo.
choice /c 12 /n /m "选择启动模式 [1/2]: "
if errorlevel 2 goto WEBUI
if errorlevel 1 goto DESKTOP

:DESKTOP
echo [Check] Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found!
    pause
    exit /b 1
)

echo [Check] Python deps...
python -c "import PIL, requests, tkinter, psutil" >nul 2>&1
if errorlevel 1 (
    echo [Install] Installing dependencies...
    python -m pip install -r "%~dp0requirements.txt" -q
)

echo [Check] Ollama...
python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=2)" >nul 2>&1
if errorlevel 1 (
    echo [Start] Starting Ollama...
    start "Ollama" ollama serve
    timeout /t 5 /nobreak >nul
) else (
    echo [OK] Ollama running
)

echo [Launch] Desktop GUI...
python "%~dp0ai_image_studio.py"
pause
exit /b 0

:WEBUI
echo [Check] Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found!
    pause
    exit /b 1
)

echo [Check] Python deps...
python -c "import gradio" >nul 2>&1
if errorlevel 1 (
    echo [Install] Installing WebUI dependencies...
    python -m pip install gradio -q
)

echo [Launch] WebUI...
echo 浏览器打开 http://127.0.0.1:7862
python "%~dp0ai_studio_web.py"
pause
exit /b 0

@echo off
title Edge Sidecar Browser
cd /d "%~dp0"

echo ========================================================
echo   Starting Edge Sidecar Browser...
echo   (1번 기능 가로채기, MS 텔레메트리 차단, 크롬 확장 호환)
echo ========================================================

python sidecar_app.py
pause

@echo off
title Edge Sidecar Browser (Isolated Profile)
cd /d "%~dp0"

echo ========================================================
echo   Starting Edge Sidecar Browser [ISOLATED PROFILE]
echo   (흔적을 남기지 않는 1회성 샌드박스 프로필)
echo ========================================================

python sidecar_app.py --profile isolated
pause

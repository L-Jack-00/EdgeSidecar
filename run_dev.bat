@echo off
title Edge Sidecar Browser (Developer Profile)
cd /d "%~dp0"

echo ========================================================
echo   Starting Edge Sidecar Browser [DEVELOPER PROFILE]
echo   (패킷 분석, 헤더 변조, 전역 CORS 해제 활성화)
echo ========================================================

python sidecar_app.py --profile developer
pause

@echo off
title PLAYFy TV - Production Engine
echo ===================================================
echo   PLAYFy TV - Production React & Streaming Engine
echo ===================================================
echo [1/2] Opening application in browser at http://127.0.0.1:8000 ...
start "" http://127.0.0.1:8000
echo [2/2] Launching backend server on port 8000 ...
python server.py
pause

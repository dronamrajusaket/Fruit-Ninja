@echo off
title Fruit Ninja - 2 Player Hand Tracking
cd /d "%~dp0"
echo Starting Fruit Ninja 2-Player Edition...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Game terminated with an error code %ERRORLEVEL%.
    pause
)

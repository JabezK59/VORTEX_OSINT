@echo off
title VORTEX OSINT Suite
echo Launching VORTEX OSINT GUI...
python main.py
if errorlevel 1 (
    echo.
    echo An error occurred while running VORTEX OSINT.
    pause
)

@echo off
cd /d "%~dp0"
pythonw launcher.py
if errorlevel 1 (
    python launcher.py
    if errorlevel 1 (
        py launcher.py
        if errorlevel 1 (
            echo.
            echo Error: Could not find Python. Please install Python from https://www.python.org/downloads/
            echo Make sure to check "Add Python to PATH" during installation.
            pause
        )
    )
)

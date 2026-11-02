@echo off
title Nexus AI Assistant
cd /d "%~dp0"
".venv\Scripts\python.exe" "main.py"
if %errorlevel% neq 0 pause

@echo off
chcp 65001 >nul
set PYTHONUTF8=1
title Casper Loto - local preview
"%~dp0..\.venv\Scripts\python.exe" "%~dp0local_preview.py"
if errorlevel 1 pause

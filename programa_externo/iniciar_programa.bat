@echo off
REM Abre el programa externo de CARTESIANA (solo usa la biblioteca estandar de Python).
set PY=C:\Users\wence\AppData\Local\Python\pythoncore-3.14-64\python.exe
if not exist "%PY%" set PY=python
cd /d "%~dp0"
"%PY%" cartesiana_app.py
if errorlevel 1 pause

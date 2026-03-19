@echo off
setlocal

cd /d "%~dp0"

if not defined WANGP_HOST set WANGP_HOST=0.0.0.0
if not defined WANGP_PORT set WANGP_PORT=8100
if not defined WANGP_UPLOAD_DIR set WANGP_UPLOAD_DIR=uploads
if not defined WANGP_OUTPUT_DIR set WANGP_OUTPUT_DIR=output

if not defined WANGP_API_KEY (
    echo WARNING: WANGP_API_KEY is not set. The server will accept unauthenticated requests.
)

set PYTHON=python
if exist ".venv\Scripts\python.exe" set PYTHON=.venv\Scripts\python.exe

echo Starting Wan2GP REST API on %WANGP_HOST%:%WANGP_PORT%...
%PYTHON% -m server.main

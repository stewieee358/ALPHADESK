@echo off
title ALPHADESK Launcher
cd /d "%~dp0"
set counter=0

echo.
echo   ALPHADESK
echo   ==============
echo.

REM -- Check uv is available --------------------------------------------------
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo   ERROR: 'uv' was not found in PATH.
    echo   Install uv from: https://docs.astral.sh/uv/
    echo.
    pause
    exit /b 1
)

REM -- Already running? -------------------------------------------------------
powershell -Command "try{Invoke-WebRequest 'http://localhost:8000/api/status' -UseBasicParsing -TimeoutSec 1|Out-Null;exit 0}catch{exit 1}" 2>nul
if %errorlevel%==0 (
    echo   Already running -- opening browser.
    start "" "http://localhost:8000"
    goto :eof
)

REM -- Start server -----------------------------------------------------------
echo   Starting server...
start "ALPHADESK Server" /min cmd /c "uv run uvicorn mini_bloomberg.web.server:app --port 8000"

REM -- Poll until ready (max 20 s) --------------------------------------------
echo   Waiting for server to be ready...

:waitloop
timeout /t 1 /nobreak >nul
powershell -Command "try{Invoke-WebRequest 'http://localhost:8000/api/status' -UseBasicParsing -TimeoutSec 1|Out-Null;exit 0}catch{exit 1}" 2>nul
if %errorlevel%==0 goto :open
set /a counter+=1
if %counter% geq 20 goto :timeout
goto :waitloop

:timeout
echo.
echo   ERROR: Server did not start within 20 seconds.
echo   Check the "ALPHADESK Server" window for error details.
echo.
pause
exit /b 1

:open
echo.
echo   Ready!  Opening http://localhost:8000
echo.
start "" "http://localhost:8000"
echo   The server is running in the "ALPHADESK Server" window.
echo   Close that window (or press Ctrl+C in it) to stop the server.
echo.
pause

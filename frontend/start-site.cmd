@echo off
set "VITE=%~dp0node_modules\.bin\vite.cmd"

if not exist "%VITE%" goto missing_dependencies
if not exist "%~dp0dist\index.html" goto missing_build

start "IT Platform Preview" /min "%VITE%" preview --configLoader runner --host 127.0.0.1 --port 3000
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:3000/"
exit /b 0

:missing_dependencies
echo Frontend dependencies not found.
echo Run pnpm install first.
pause
exit /b 1

:missing_build
echo Production build not found:
echo %~dp0dist\index.html
pause
exit /b 1

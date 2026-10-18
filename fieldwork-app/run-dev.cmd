@echo off
REM Starts the Fieldwork app with the portable Node (no admin rights needed).
set "NODE_HOME=%LOCALAPPDATA%\Programs\node\node-v24.19.0-win-x64"
set "PATH=%NODE_HOME%;%PATH%"
cd /d "%~dp0"
if not exist node_modules (
  echo Installing packages the first time...
  call npm.cmd install
)
echo.
echo Fieldwork is starting. Open http://localhost:3000 in your browser.
echo Close this window to stop it.
echo.
call npm.cmd run dev
echo.
echo Fieldwork stopped. If you saw "Another next dev server is already running", close the other copy first.
pause

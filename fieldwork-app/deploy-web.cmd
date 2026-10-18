@echo off
REM Deploys the Next.js app as a second Cloud Run service (fieldwork-web). Run ..\fieldwork-ai\deploy.cmd first.
set "GCLOUD=%LOCALAPPDATA%\Google\google-cloud-sdk\bin\gcloud.cmd"
set "REGION=asia-southeast1"
cd /d "%~dp0"

for /f %%i in ('call "%GCLOUD%" run services describe fieldwork-api --region %REGION% --format^="value(status.url)"') do set "API_URL=%%i"
echo API: %API_URL%
echo NEXT_PUBLIC_API_BASE=%API_URL%> .env.production

call "%GCLOUD%" run deploy fieldwork-web --source . --region %REGION% --memory 512Mi --allow-unauthenticated
del .env.production

for /f %%i in ('call "%GCLOUD%" run services describe fieldwork-web --region %REGION% --format^="value(status.url)"') do set "WEB_URL=%%i"
echo Web: %WEB_URL%
REM Allow the web origin to call the API (CORS).
call "%GCLOUD%" run services update fieldwork-api --region %REGION% --update-env-vars FW_CORS_ORIGINS=%WEB_URL%
pause

@echo off
REM Builds the Fieldwork API on Google Cloud Build and deploys it to Cloud Run (Singapore).
REM Run cloud-setup.cmd once before this.
set "GCLOUD=%LOCALAPPDATA%\Google\google-cloud-sdk\bin\gcloud.cmd"
set "REGION=asia-southeast1"
set "PROJECT=project-5c967997-3711-4585-9ed"
set "BUCKET=%PROJECT%-fieldwork"
cd /d "%~dp0"

REM Store the Gemini key in Secret Manager the first time (read from your Windows user variable).
call "%GCLOUD%" secrets describe gemini-api-key >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "[IO.File]::WriteAllText('%TEMP%\fw_key.txt', [Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User'))"
  call "%GCLOUD%" secrets create gemini-api-key --data-file="%TEMP%\fw_key.txt"
  del "%TEMP%\fw_key.txt"
)

REM Cloud Storage bucket and Firestore (native mode) database, created only if missing.
call "%GCLOUD%" storage buckets describe gs://%BUCKET% >nul 2>&1
if errorlevel 1 call "%GCLOUD%" storage buckets create gs://%BUCKET% --location=%REGION% --uniform-bucket-level-access
call "%GCLOUD%" firestore databases describe --database="(default)" >nul 2>&1
if errorlevel 1 call "%GCLOUD%" firestore databases create --database="(default)" --location=%REGION% --type=firestore-native

REM Let the Cloud Run service account (default compute SA) use Firestore, Storage and Vertex AI.
for /f %%i in ('call "%GCLOUD%" projects describe %PROJECT% --format^="value(projectNumber)"') do set "PNUM=%%i"
set "SA=%PNUM%-compute@developer.gserviceaccount.com"
for %%r in (roles/datastore.user roles/storage.objectAdmin roles/aiplatform.user) do (
  call "%GCLOUD%" projects add-iam-policy-binding %PROJECT% --member=serviceAccount:%SA% --role=%%r --condition=None >nul
)

call "%GCLOUD%" run deploy fieldwork-api --source . --region %REGION% ^
  --memory 4Gi --cpu 2 --min-instances 1 --timeout 600 --allow-unauthenticated ^
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest ^
  --set-env-vars FW_USE_VERTEX=1,FW_GCP_PROJECT=%PROJECT%,FW_GCP_LOCATION=global,FW_STORE=cloud,FW_BUCKET=%BUCKET%
pause

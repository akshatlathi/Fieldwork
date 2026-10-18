@echo off
REM One-time Google Cloud setup for Fieldwork. Double-click it; a browser opens for sign-in.
set "GCLOUD=%LOCALAPPDATA%\Google\google-cloud-sdk\bin\gcloud.cmd"
set "PROJECT=project-5c967997-3711-4585-9ed"

echo Step 1 of 3: sign in with the Google account that owns the Fieldwork project.
call "%GCLOUD%" auth login
call "%GCLOUD%" auth application-default login

echo.
echo Step 2 of 3: select the project.
call "%GCLOUD%" config set project %PROJECT%

echo.
echo Step 3 of 3: turn on the services Fieldwork uses (takes a minute).
call "%GCLOUD%" services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com firestore.googleapis.com storage.googleapis.com

echo.
echo Done.
pause

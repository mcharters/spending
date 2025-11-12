@echo off
REM Local build script for frontend (Windows)

echo Building frontend for deployment...

REM Navigate to frontend directory
cd frontend

REM Install dependencies
echo Installing npm dependencies...
call npm install

REM Build the React app
echo Building React app...
call npm run build

cd ..

echo.
echo Frontend built successfully to backend/static/
echo Ready to commit and push to Railway

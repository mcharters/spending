@echo off
echo Running all tests for Spending Tracker...
echo.

echo ========================================
echo [1/2] Running Backend Tests (pytest)
echo ========================================
cd backend
call venv\Scripts\activate
pytest -v
set BACKEND_EXIT_CODE=%ERRORLEVEL%
cd ..

echo.
echo ========================================
echo [2/2] Running Frontend Tests (Jest)
echo ========================================
cd frontend
call npm test -- --passWithNoTests --watchAll=false
set FRONTEND_EXIT_CODE=%ERRORLEVEL%
cd ..

echo.
echo ========================================
echo Test Results Summary
echo ========================================
if %BACKEND_EXIT_CODE% EQU 0 (
    echo Backend Tests:  PASSED ✓
) else (
    echo Backend Tests:  FAILED ✗
)

if %FRONTEND_EXIT_CODE% EQU 0 (
    echo Frontend Tests: PASSED ✓
) else (
    echo Frontend Tests: FAILED ✗
)

echo.
if %BACKEND_EXIT_CODE% EQU 0 if %FRONTEND_EXIT_CODE% EQU 0 (
    echo All tests passed! ✓
    exit /b 0
) else (
    echo Some tests failed! ✗
    exit /b 1
)

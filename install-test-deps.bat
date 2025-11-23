@echo off
echo Installing test dependencies...
echo.

echo [1/2] Installing backend test dependencies...
cd backend
call venv\Scripts\activate
pip install -r requirements-dev.txt
cd ..

echo.
echo [2/2] Installing frontend test dependencies...
cd frontend
call npm install
cd ..

echo.
echo Test dependencies installed successfully!
echo.
echo To run tests:
echo   Backend:  cd backend ^&^& venv\Scripts\activate ^&^& pytest
echo   Frontend: cd frontend ^&^& npm test

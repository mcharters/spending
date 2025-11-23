#!/bin/bash
echo "Installing test dependencies..."
echo ""

echo "[1/2] Installing backend test dependencies..."
cd backend
source venv/bin/activate
pip install -r requirements-dev.txt
cd ..

echo ""
echo "[2/2] Installing frontend test dependencies..."
cd frontend
npm install
cd ..

echo ""
echo "Test dependencies installed successfully!"
echo ""
echo "To run tests:"
echo "  Backend:  cd backend && source venv/bin/activate && pytest"
echo "  Frontend: cd frontend && npm test"

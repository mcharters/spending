#!/bin/bash
echo "Running all tests for Spending Tracker..."
echo ""

echo "========================================"
echo "[1/2] Running Backend Tests (pytest)"
echo "========================================"
cd backend
source venv/bin/activate
pytest -v
BACKEND_EXIT_CODE=$?
cd ..

echo ""
echo "========================================"
echo "[2/2] Running Frontend Tests (Jest)"
echo "========================================"
cd frontend
npm test -- --passWithNoTests --watchAll=false
FRONTEND_EXIT_CODE=$?
cd ..

echo ""
echo "========================================"
echo "Test Results Summary"
echo "========================================"
if [ $BACKEND_EXIT_CODE -eq 0 ]; then
    echo "Backend Tests:  PASSED ✓"
else
    echo "Backend Tests:  FAILED ✗"
fi

if [ $FRONTEND_EXIT_CODE -eq 0 ]; then
    echo "Frontend Tests: PASSED ✓"
else
    echo "Frontend Tests: FAILED ✗"
fi

echo ""
if [ $BACKEND_EXIT_CODE -eq 0 ] && [ $FRONTEND_EXIT_CODE -eq 0 ]; then
    echo "All tests passed! ✓"
    exit 0
else
    echo "Some tests failed! ✗"
    exit 1
fi

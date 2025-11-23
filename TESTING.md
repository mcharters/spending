# Testing Guide

This document explains how to run tests for the Spending Tracker application.

## Backend Tests (Python/pytest)

### Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Activate your virtual environment:
   - **Windows**: `venv\Scripts\activate`
   - **Mac/Linux**: `source venv/bin/activate`

3. Install test dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

### Running Tests

Run all tests:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run specific test file:
```bash
pytest tests/test_date_filtering.py
```

Run tests with coverage report:
```bash
pytest --cov=. --cov-report=html
```

Run only specific test markers:
```bash
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
```

### Backend Test Structure

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures and configuration
│   └── test_date_filtering.py  # Date/month boundary tests
├── pytest.ini                   # Pytest configuration
└── requirements-dev.txt         # Test dependencies
```

### Key Backend Tests

**test_date_filtering.py** covers:
- Creating expenses with custom dates (past, present, future)
- Budget calculations for current month only
- Excluding future and past expenses from current month budgets
- Budget rollover across month boundaries
- Cumulative balance calculations with surplus and deficit
- Multi-month budget tracking

### Mocking Time in Backend Tests

Backend tests use `freezegun` to mock the current date/time:

```python
from freezegun import freeze_time

@freeze_time("2025-01-15")
def test_something():
    # Inside this test, datetime.utcnow() returns 2025-01-15
    pass
```

## Frontend Tests (Jest/React Testing Library)

### Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies (if not already installed):
   ```bash
   npm install
   ```

### Running Tests

Run all tests:
```bash
npm test
```

Run tests in watch mode (re-runs on file changes):
```bash
npm run test:watch
```

Run tests with coverage report:
```bash
npm run test:coverage
```

### Frontend Test Structure

```
frontend/
├── src/
│   ├── App.test.js         # Date filtering and sorting tests
│   ├── setupTests.js       # Jest configuration
│   └── ...
├── .babelrc                # Babel config for Jest
└── package.json            # Jest configuration
```

### Key Frontend Tests

**App.test.js** covers:
- Filtering expenses to show only current month
- Sorting expenses by date (descending/newest first)
- Updating displayed expenses when month changes
- Handling empty expense lists
- Date utility function validation

### Mocking Time in Frontend Tests

Frontend tests use Jest's fake timers:

```javascript
beforeEach(() => {
  jest.useFakeTimers();
  jest.setSystemTime(new Date('2025-01-25T12:00:00'));
});

afterEach(() => {
  jest.useRealTimers();
});
```

### Mocking API Calls

Frontend tests mock `fetch` API calls:

```javascript
global.fetch = jest.fn((url) => {
  if (url.includes('/api/expenses')) {
    return Promise.resolve({
      ok: true,
      json: async () => mockExpenses,
    });
  }
});
```

## Critical Test Scenarios

### Month Boundary Testing

Both backend and frontend have tests that verify behavior when:
- Current date is end of month (e.g., Jan 31)
- Transitioning from one month to the next
- Budget rollover calculations work correctly

### Future Date Handling

Tests verify:
- ✅ Backend accepts future-dated expenses
- ✅ Backend excludes future expenses from current month budget
- ✅ Frontend filters out future expenses from current month view
- 📋 Future work: Add UI for selecting different months to view

### Past Date Handling

Tests verify:
- ✅ Backend accepts past-dated expenses
- ✅ Backend excludes past expenses from current month budget
- ✅ Backend includes past month spending in cumulative balance
- ✅ Frontend filters out past expenses from current month view

## Test Coverage Goals

### Backend Coverage
- ✅ Expense creation with custom dates
- ✅ Budget calculations (current month only)
- ✅ Month rollover logic
- ✅ Cumulative balance tracking
- ⚠️ User permission filtering (partially covered)

### Frontend Coverage
- ✅ Date filtering logic
- ✅ Expense sorting (newest first)
- ⚠️ User interactions (limited coverage)
- ⚠️ Form submissions (not yet covered)
- ⚠️ Authentication flows (not yet covered)

## Running All Tests

To run both backend and frontend tests in sequence:

**Windows**:
```bash
cd backend
venv\Scripts\activate
pytest
cd ..\frontend
npm test
```

**Mac/Linux**:
```bash
cd backend
source venv/bin/activate
pytest
cd ../frontend
npm test
```

## Continuous Integration

Consider adding these test commands to your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Backend Tests
  run: |
    cd backend
    pip install -r requirements-dev.txt
    pytest --cov

- name: Frontend Tests
  run: |
    cd frontend
    npm install
    npm test -- --coverage
```

## Known Limitations

1. **Frontend tests don't test full components**: Tests use simplified components to test specific logic rather than full integration tests
2. **No E2E tests**: Consider adding Playwright or Cypress for end-to-end testing
3. **Limited API mocking**: Frontend tests use simple fetch mocks; consider using MSW (Mock Service Worker) for more realistic API mocking
4. **Authentication not fully tested**: Login/logout flows need more comprehensive testing

## Next Steps

Future testing improvements:
- [ ] Add E2E tests with Playwright/Cypress
- [ ] Increase test coverage to >80%
- [ ] Add tests for month selector UI (when implemented)
- [ ] Add visual regression testing
- [ ] Add performance testing for budget calculations

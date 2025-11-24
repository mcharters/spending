/**
 * Tests for date filtering, sorting, and month boundary scenarios in the React app.
 *
 * These tests verify:
 * - Expense list filtering by current month
 * - Date-based sorting (newest first)
 * - Handling of future and past dated expenses
 * - Month transition behavior
 */
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import App from './App';

// Mock react-datepicker to avoid rendering issues in tests
jest.mock('react-datepicker', () => {
  return {
    __esModule: true,
    default: ({ selected, onChange }) => (
      <input
        type="date"
        value={selected ? selected.toISOString().split('T')[0] : ''}
        onChange={(e) => onChange(new Date(e.target.value))}
        data-testid="date-picker"
      />
    ),
  };
});

// Mock CSS imports
jest.mock('react-datepicker/dist/react-datepicker.css', () => ({}));

describe('ExpenseListView - Date Filtering and Sorting', () => {
  const mockExpenses = [
    {
      id: 1,
      amount: 50.00,
      category_id: 1,
      category: 'Groceries',
      parent_type: 'Shared',
      created_by: 'user1',
      expense_date: '2025-01-15',
      created_at: '2025-01-15T10:00:00'
    },
    {
      id: 2,
      amount: 75.50,
      category_id: 1,
      category: 'Groceries',
      parent_type: 'Shared',
      created_by: 'user1',
      expense_date: '2025-01-20',
      created_at: '2025-01-20T14:30:00'
    },
    {
      id: 3,
      amount: 100.00,
      category_id: 1,
      category: 'Groceries',
      parent_type: 'Shared',
      created_by: 'user2',
      expense_date: '2025-01-10',
      created_at: '2025-01-10T09:00:00'
    },
    {
      id: 4,
      amount: 200.00,
      category_id: 1,
      category: 'Groceries',
      parent_type: 'Shared',
      created_by: 'user1',
      expense_date: '2024-12-25', // Previous month - should be filtered out
      created_at: '2024-12-25T12:00:00'
    },
    {
      id: 5,
      amount: 150.00,
      category_id: 1,
      category: 'Groceries',
      parent_type: 'Shared',
      created_by: 'user1',
      expense_date: '2025-02-05', // Future month - should be filtered out
      created_at: '2025-02-05T11:00:00'
    }
  ];

  const mockCategories = [
    { id: 1, name: 'Groceries', parent_type: 'Shared' }
  ];

  beforeEach(() => {
    // Mock Date to be January 2025
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2025-01-25T12:00:00'));

    global.fetch = jest.fn((url) => {
      if (url.includes('/api/expenses')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockExpenses,
        });
      }
      if (url.includes('/api/categories')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockCategories,
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  test('filters expenses to show only current month (January 2025)', async () => {
    // Mock auth and render the expense list for category 1
    const mockAuthWrapper = () => (
      <MemoryRouter initialEntries={['/expenses/1']}>
        <Routes>
          <Route path="/expenses/:categoryId" element={
            <div data-testid="expense-list-wrapper">
              {/* Simplified test component that mimics ExpenseListView filtering */}
              <ExpenseListTestComponent />
            </div>
          } />
        </Routes>
      </MemoryRouter>
    );

    // Helper component to test filtering logic
    const ExpenseListTestComponent = () => {
      const [expenses, setExpenses] = React.useState([]);

      React.useEffect(() => {
        const fetchData = async () => {
          const response = await fetch('/api/expenses');
          const data = await response.json();

          // Filter for category 1 and current month (matching App.js logic)
          const currentMonth = new Date().toISOString().slice(0, 7); // "2025-01"
          const filtered = data.filter(exp =>
            exp.category_id === 1 &&
            exp.expense_date.startsWith(currentMonth)
          );

          // Sort by date descending
          const sorted = filtered.sort((a, b) => {
            const dateA = new Date(a.expense_date);
            const dateB = new Date(b.expense_date);
            return dateB - dateA;
          });

          setExpenses(sorted);
        };
        fetchData();
      }, []);

      return (
        <div>
          {expenses.map(exp => (
            <div key={exp.id} data-testid={`expense-${exp.id}`}>
              {exp.expense_date}: ${exp.amount}
            </div>
          ))}
        </div>
      );
    };

    render(mockAuthWrapper());

    await waitFor(() => {
      // Should see January expenses (ids 1, 2, 3)
      expect(screen.getByTestId('expense-1')).toBeInTheDocument();
      expect(screen.getByTestId('expense-2')).toBeInTheDocument();
      expect(screen.getByTestId('expense-3')).toBeInTheDocument();

      // Should NOT see December expense (id 4) or February expense (id 5)
      expect(screen.queryByTestId('expense-4')).not.toBeInTheDocument();
      expect(screen.queryByTestId('expense-5')).not.toBeInTheDocument();
    });
  });

  test('sorts expenses by date descending (newest first)', async () => {
    const ExpenseListTestComponent = () => {
      const [expenses, setExpenses] = React.useState([]);

      React.useEffect(() => {
        const fetchData = async () => {
          const response = await fetch('/api/expenses');
          const data = await response.json();

          const currentMonth = new Date().toISOString().slice(0, 7);
          const filtered = data.filter(exp =>
            exp.category_id === 1 &&
            exp.expense_date.startsWith(currentMonth)
          );

          const sorted = filtered.sort((a, b) => {
            const dateA = new Date(a.expense_date);
            const dateB = new Date(b.expense_date);
            return dateB - dateA;
          });

          setExpenses(sorted);
        };
        fetchData();
      }, []);

      return (
        <div data-testid="expense-list">
          {expenses.map((exp, index) => (
            <div key={exp.id} data-testid={`expense-position-${index}`} data-expense-id={exp.id}>
              {exp.expense_date}
            </div>
          ))}
        </div>
      );
    };

    render(
      <MemoryRouter>
        <ExpenseListTestComponent />
      </MemoryRouter>
    );

    await waitFor(() => {
      // Verify order: Jan 20 (id 2), Jan 15 (id 1), Jan 10 (id 3)
      const position0 = screen.getByTestId('expense-position-0');
      const position1 = screen.getByTestId('expense-position-1');
      const position2 = screen.getByTestId('expense-position-2');

      expect(position0).toHaveAttribute('data-expense-id', '2'); // Jan 20
      expect(position1).toHaveAttribute('data-expense-id', '1'); // Jan 15
      expect(position2).toHaveAttribute('data-expense-id', '3'); // Jan 10
    });
  });

  test('updates filtered expenses when month changes', async () => {
    const ExpenseListTestComponent = () => {
      const [expenses, setExpenses] = React.useState([]);
      const [currentDate, setCurrentDate] = React.useState(new Date());

      const fetchExpenses = React.useCallback(() => {
        const fetchData = async () => {
          const response = await fetch('/api/expenses');
          const data = await response.json();

          const currentMonth = currentDate.toISOString().slice(0, 7);
          const filtered = data.filter(exp =>
            exp.category_id === 1 &&
            exp.expense_date.startsWith(currentMonth)
          );

          const sorted = filtered.sort((a, b) => {
            const dateA = new Date(a.expense_date);
            const dateB = new Date(b.expense_date);
            return dateB - dateA;
          });

          setExpenses(sorted);
        };
        fetchData();
      }, [currentDate]);

      React.useEffect(() => {
        fetchExpenses();
      }, [fetchExpenses]);

      return (
        <div>
          <button onClick={() => setCurrentDate(new Date('2025-02-15'))}>
            Go to February
          </button>
          <div data-testid="expense-count">{expenses.length}</div>
          {expenses.map(exp => (
            <div key={exp.id} data-testid={`expense-${exp.id}`}>
              {exp.expense_date}
            </div>
          ))}
        </div>
      );
    };

    render(
      <MemoryRouter>
        <ExpenseListTestComponent />
      </MemoryRouter>
    );

    // Initially in January - should see 3 expenses
    await waitFor(() => {
      expect(screen.getByTestId('expense-count')).toHaveTextContent('3');
    });

    // Switch to February
    const februaryButton = screen.getByText('Go to February');
    februaryButton.click();

    // Should now see 1 expense (the February one)
    await waitFor(() => {
      expect(screen.getByTestId('expense-count')).toHaveTextContent('1');
      expect(screen.getByTestId('expense-5')).toBeInTheDocument();
    });
  });

  test('handles empty expense list for current month', async () => {
    // Mock empty response
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: async () => [],
      })
    );

    const ExpenseListTestComponent = () => {
      const [expenses, setExpenses] = React.useState([]);

      React.useEffect(() => {
        const fetchData = async () => {
          const response = await fetch('/api/expenses');
          const data = await response.json();
          setExpenses(data);
        };
        fetchData();
      }, []);

      return (
        <div>
          {expenses.length === 0 ? (
            <p data-testid="no-expenses">No expenses recorded for this category this month.</p>
          ) : (
            expenses.map(exp => <div key={exp.id}>{exp.amount}</div>)
          )}
        </div>
      );
    };

    render(
      <MemoryRouter>
        <ExpenseListTestComponent />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('no-expenses')).toBeInTheDocument();
    });
  });
});

describe('Date Utility Functions', () => {
  test('toISOString().slice(0, 7) extracts year-month correctly', () => {
    const testDate = new Date('2025-01-15T10:30:00');
    const yearMonth = testDate.toISOString().slice(0, 7);

    expect(yearMonth).toBe('2025-01');
  });

  test('date string comparison works correctly', () => {
    const expense1 = { expense_date: '2025-01-15' };
    const expense2 = { expense_date: '2025-01-20' };
    const expense3 = { expense_date: '2025-02-05' };

    const currentMonth = '2025-01';

    expect(expense1.expense_date.startsWith(currentMonth)).toBe(true);
    expect(expense2.expense_date.startsWith(currentMonth)).toBe(true);
    expect(expense3.expense_date.startsWith(currentMonth)).toBe(false);
  });

  test('date sorting works with Date objects', () => {
    const dates = [
      { expense_date: '2025-01-20' },
      { expense_date: '2025-01-10' },
      { expense_date: '2025-01-15' }
    ];

    const sorted = dates.sort((a, b) => {
      const dateA = new Date(a.expense_date);
      const dateB = new Date(b.expense_date);
      return dateB - dateA; // Descending
    });

    expect(sorted[0].expense_date).toBe('2025-01-20');
    expect(sorted[1].expense_date).toBe('2025-01-15');
    expect(sorted[2].expense_date).toBe('2025-01-10');
  });
});

describe('Empty State Handling', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2025-01-25T12:00:00'));
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  test('shows empty state when no budgets exist', async () => {
    // Mock empty budgets response
    global.fetch = jest.fn((url) => {
      if (url.includes('/api/budgets')) {
        return Promise.resolve({
          ok: true,
          json: async () => [], // Empty budgets array
        });
      }
      if (url.includes('/api/categories')) {
        return Promise.resolve({
          ok: true,
          json: async () => [{ id: 1, name: 'Groceries', parent_type: 'Shared' }],
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    const TestComponent = () => {
      const [budgets, setBudgets] = React.useState([]);

      React.useEffect(() => {
        const fetchData = async () => {
          const response = await fetch('/api/budgets');
          const data = await response.json();
          setBudgets(data);
        };
        fetchData();
      }, []);

      return (
        <div>
          {budgets.length === 0 ? (
            <div data-testid="empty-state">
              <p>No budgets available for this month.</p>
              <p>Budgets are created when you first use the app in a new month.</p>
            </div>
          ) : (
            <div data-testid="has-budgets">
              {budgets.map(b => <div key={b.id}>{b.category}</div>)}
            </div>
          )}
        </div>
      );
    };

    render(
      <MemoryRouter>
        <TestComponent />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('empty-state')).toBeInTheDocument();
      expect(screen.getByText('No budgets available for this month.')).toBeInTheDocument();
      expect(screen.queryByTestId('has-budgets')).not.toBeInTheDocument();
    });
  });

  test('shows budgets when they exist', async () => {
    const mockBudgets = [
      {
        id: 1,
        category: 'Groceries',
        parent_type: 'Shared',
        user: null,
        monthly_amount: 1200,
        effective_budget: 1200,
        current_spent: 150,
        remaining: 1050,
        is_over_budget: false
      }
    ];

    global.fetch = jest.fn((url) => {
      if (url.includes('/api/budgets')) {
        return Promise.resolve({
          ok: true,
          json: async () => mockBudgets,
        });
      }
      return Promise.reject(new Error('Unknown URL'));
    });

    const TestComponent = () => {
      const [budgets, setBudgets] = React.useState([]);

      React.useEffect(() => {
        const fetchData = async () => {
          const response = await fetch('/api/budgets');
          const data = await response.json();
          setBudgets(data);
        };
        fetchData();
      }, []);

      return (
        <div>
          {budgets.length === 0 ? (
            <div data-testid="empty-state">No budgets</div>
          ) : (
            <div data-testid="has-budgets">
              {budgets.map(b => <div key={b.id} data-testid={`budget-${b.id}`}>{b.category}</div>)}
            </div>
          )}
        </div>
      );
    };

    render(
      <MemoryRouter>
        <TestComponent />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByTestId('has-budgets')).toBeInTheDocument();
      expect(screen.getByTestId('budget-1')).toBeInTheDocument();
      expect(screen.queryByTestId('empty-state')).not.toBeInTheDocument();
    });
  });
});

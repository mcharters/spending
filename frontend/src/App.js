import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

function App() {
  return (
    <Router>
      <AuthWrapper />
    </Router>
  );
}

function AuthWrapper() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [loginError, setLoginError] = useState('');

  const API_URL = process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:5000/api';

  const getAuthHeader = () => {
    const token = btoa(`${credentials.username}:${credentials.password}`);
    return { 'Authorization': `Basic ${token}` };
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');

    try {
      const token = btoa(`${loginForm.username}:${loginForm.password}`);
      const response = await fetch(`${API_URL}/categories`, {
        headers: { 'Authorization': `Basic ${token}` }
      });

      if (response.ok) {
        setCredentials({ username: loginForm.username, password: loginForm.password });
        setIsAuthenticated(true);
        setLoginForm({ username: '', password: '' });
      } else {
        setLoginError('Invalid username or password');
      }
    } catch (error) {
      setLoginError('Error connecting to server');
      console.error('Login error:', error);
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setCredentials({ username: '', password: '' });
  };

  if (!isAuthenticated) {
    return (
      <div className="container">
        <h1>Spending Tracker</h1>
        <div className="login-container">
          <h2>Login</h2>
          <form onSubmit={handleLogin}>
            <input
              type="text"
              placeholder="Username"
              value={loginForm.username}
              onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={loginForm.password}
              onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
              required
            />
            {loginError && <p className="error-message">{loginError}</p>}
            <button type="submit">Login</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<MainView apiUrl={API_URL} getAuthHeader={getAuthHeader} handleLogout={handleLogout} setIsAuthenticated={setIsAuthenticated} />} />
      <Route path="/detail/:parentType" element={<DetailView apiUrl={API_URL} getAuthHeader={getAuthHeader} handleLogout={handleLogout} setIsAuthenticated={setIsAuthenticated} />} />
      <Route path="/expenses/:categoryId" element={<ExpenseListView apiUrl={API_URL} getAuthHeader={getAuthHeader} handleLogout={handleLogout} setIsAuthenticated={setIsAuthenticated} />} />
      <Route path="/history" element={<ExpenseHistoryView apiUrl={API_URL} getAuthHeader={getAuthHeader} handleLogout={handleLogout} setIsAuthenticated={setIsAuthenticated} />} />
    </Routes>
  );
}

function MainView({ apiUrl, getAuthHeader, handleLogout, setIsAuthenticated }) {
  const [budgets, setBudgets] = useState([]);
  const [personalSummary, setPersonalSummary] = useState(null);
  const [sharedSummary, setSharedSummary] = useState(null);
  const [categories, setCategories] = useState([]);
  const [errorMessage, setErrorMessage] = useState('');
  const [formData, setFormData] = useState({
    amount: '',
    category_id: '',
    expense_date: new Date(),
    description: ''
  });
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Get month from URL parameter, or default to current month
  const monthParam = searchParams.get('month');
  const [selectedMonth, setSelectedMonth] = useState(() => {
    if (monthParam) {
      const [year, month] = monthParam.split('-');
      return new Date(parseInt(year), parseInt(month) - 1, 1);
    }
    return new Date();
  });

  const API_URL = apiUrl;

  useEffect(() => {
    fetchBudgets();
    fetchCategories();
  }, [selectedMonth]);

  // Sync datepicker with selected month from URL
  useEffect(() => {
    setFormData(prev => ({
      ...prev,
      expense_date: new Date(selectedMonth)
    }));
  }, [selectedMonth]);

  const fetchBudgets = async () => {
    try {
      const monthStr = `${selectedMonth.getFullYear()}-${String(selectedMonth.getMonth() + 1).padStart(2, '0')}`;
      const response = await fetch(`${API_URL}/budgets?month=${monthStr}`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setBudgets(data.categories || []);
        setPersonalSummary(data.personal_summary);
        setSharedSummary(data.shared_summary);
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      } else if (response.status === 400) {
        const errorData = await response.json();
        setErrorMessage(errorData.error || 'Error fetching budgets');
      }
    } catch (error) {
      console.error('Error fetching budgets:', error);
      setErrorMessage('Error connecting to server');
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/categories`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setCategories(data);
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage(''); // Clear previous errors
    try {
      const response = await fetch(`${API_URL}/expenses`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader()
        },
        body: JSON.stringify({
          ...formData,
          amount: parseFloat(formData.amount),
          expense_date: `${formData.expense_date.getFullYear()}-${String(formData.expense_date.getMonth() + 1).padStart(2, '0')}-${String(formData.expense_date.getDate()).padStart(2, '0')}`
        })
      });

      if (response.ok) {
        setFormData({ ...formData, amount: '', category_id: '', description: '' });
        fetchBudgets();
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      } else if (response.status === 400) {
        const errorData = await response.json();
        setErrorMessage(errorData.error || 'Error creating expense');
      }
    } catch (error) {
      console.error('Error creating expense:', error);
      setErrorMessage('Error connecting to server');
    }
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const personalBudgets = budgets.filter(b => b.user !== null);
  const sharedBudgets = budgets.filter(b => b.user === null);

  // Use aggregate summaries from backend instead of summing category values
  const personalTotalBudget = personalSummary?.effective_budget || 0;
  const personalTotalSpent = personalSummary?.spent || 0;
  const personalRemaining = personalSummary?.remaining || 0;

  const sharedTotalBudget = sharedSummary?.effective_budget || 0;
  const sharedTotalSpent = sharedSummary?.spent || 0;
  const sharedRemaining = sharedSummary?.remaining || 0;

  const formatCurrency = (amount) => {
    return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const handleMonthNavigation = (direction) => {
    const newMonth = new Date(selectedMonth);
    if (direction === 'prev') {
      newMonth.setMonth(newMonth.getMonth() - 1);
    } else {
      newMonth.setMonth(newMonth.getMonth() + 1);
    }
    setSelectedMonth(newMonth);
    // Update URL parameter
    const monthStr = `${newMonth.getFullYear()}-${String(newMonth.getMonth() + 1).padStart(2, '0')}`;
    navigate(`/?month=${monthStr}`, { replace: true });
  };

  return (
    <div className="container">
      <div className="form-container">
        <form onSubmit={handleSubmit}>
          <div className="date-picker-container">
            <label>Select Date</label>
            <DatePicker
              selected={formData.expense_date}
              onChange={(date) => {
                setFormData({ ...formData, expense_date: date });
              }}
              dateFormat="MMMM d, yyyy"
              inline
              calendarStartDay={0}
              showPopperArrow={false}
              renderCustomHeader={({
                date,
                decreaseMonth,
                increaseMonth,
                prevMonthButtonDisabled,
                nextMonthButtonDisabled,
              }) => (
                <div className="custom-header">
                  <button
                    type="button"
                    onClick={() => {
                      decreaseMonth();
                      handleMonthNavigation('prev');
                    }}
                    disabled={prevMonthButtonDisabled}
                    className="nav-button"
                  >
                    ‹
                  </button>
                  <span className="month-year">
                    {date.toLocaleString('default', { month: 'long', year: 'numeric' })}
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      increaseMonth();
                      handleMonthNavigation('next');
                    }}
                    disabled={nextMonthButtonDisabled}
                    className="nav-button"
                  >
                    ›
                  </button>
                </div>
              )}
            />
          </div>
          <select
            name="category_id"
            value={formData.category_id}
            onChange={handleChange}
            required
          >
            <option value="">Select a category...</option>
            <optgroup label="Personal">
              {categories
                .filter(cat => cat.parent_type === 'Personal')
                .map(cat => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
            </optgroup>
            <optgroup label="Shared">
              {categories
                .filter(cat => cat.parent_type === 'Shared')
                .map(cat => (
                  <option key={cat.id} value={cat.id}>
                    {cat.name}
                  </option>
                ))}
            </optgroup>
          </select>
          <input
            type="number"
            name="amount"
            placeholder="Amount"
            step="0.01"
            value={formData.amount}
            onChange={handleChange}
            required
          />
          <input
            type="text"
            name="description"
            placeholder="Description (optional)"
            value={formData.description}
            onChange={handleChange}
            maxLength="200"
          />
          <button type="submit">Add Expense</button>
          {errorMessage && <p className="error-message">{errorMessage}</p>}
        </form>
      </div>

      <div className="summary-container">
        {budgets.length === 0 ? (
          <div className="empty-state">
            <p>No budgets available for this month.</p>
            <p>Budgets are created when you first use the app in a new month.</p>
          </div>
        ) : (
          <div className="summary-cards">
            {personalBudgets.length > 0 && (
              <div className="summary-card clickable" onClick={() => {
                const monthStr = `${selectedMonth.getFullYear()}-${String(selectedMonth.getMonth() + 1).padStart(2, '0')}`;
                navigate(`/detail/Personal?month=${monthStr}`);
              }}>
                <h3>Personal Spending</h3>
                <div className="summary-amount">
                  <span className="spent">${formatCurrency(personalTotalSpent)}</span>
                  <span className="separator"> / </span>
                  <span className="budget">${formatCurrency(personalTotalBudget)}</span>
                </div>
                <div className={`remaining ${personalRemaining < 0 ? 'over-budget' : ''}`}>
                  {personalRemaining < 0 ? 'Over by' : 'Remaining'}: ${formatCurrency(Math.abs(personalRemaining))}
                </div>
                <div className="progress-bar">
                  <div
                    className={`progress-fill ${personalRemaining < 0 ? 'over-budget' : ''}`}
                    style={{ width: `${Math.min((personalTotalSpent / personalTotalBudget) * 100, 100)}%` }}
                  ></div>
                </div>
              </div>
            )}

            {sharedBudgets.length > 0 && (
              <div className="summary-card clickable" onClick={() => {
                const monthStr = `${selectedMonth.getFullYear()}-${String(selectedMonth.getMonth() + 1).padStart(2, '0')}`;
                navigate(`/detail/Shared?month=${monthStr}`);
              }}>
                <h3>Shared Spending</h3>
                <div className="summary-amount">
                  <span className="spent">${formatCurrency(sharedTotalSpent)}</span>
                  <span className="separator"> / </span>
                  <span className="budget">${formatCurrency(sharedTotalBudget)}</span>
                </div>
                <div className={`remaining ${sharedRemaining < 0 ? 'over-budget' : ''}`}>
                  {sharedRemaining < 0 ? 'Over by' : 'Remaining'}: ${formatCurrency(Math.abs(sharedRemaining))}
                </div>
                <div className="progress-bar">
                  <div
                    className={`progress-fill ${sharedRemaining < 0 ? 'over-budget' : ''}`}
                    style={{ width: `${Math.min((sharedTotalSpent / sharedTotalBudget) * 100, 100)}%` }}
                  ></div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      <footer className="footer">
        <button onClick={() => navigate('/history')} className="history-link-btn">View History</button>
        <button onClick={handleLogout} className="logout-btn">Logout</button>
      </footer>
    </div>
  );
}

function DetailView({ apiUrl, getAuthHeader, handleLogout, setIsAuthenticated }) {
  const [budgets, setBudgets] = useState([]);
  const { parentType } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Get month from URL parameter, or default to current month
  const monthParam = searchParams.get('month');
  const [selectedMonth, setSelectedMonth] = useState(() => {
    if (monthParam) {
      const [year, month] = monthParam.split('-');
      return new Date(parseInt(year), parseInt(month) - 1, 1);
    }
    return new Date();
  });

  const API_URL = apiUrl;

  useEffect(() => {
    fetchBudgets();
  }, [selectedMonth]);

  const fetchBudgets = async () => {
    try {
      const monthStr = `${selectedMonth.getFullYear()}-${String(selectedMonth.getMonth() + 1).padStart(2, '0')}`;
      const response = await fetch(`${API_URL}/budgets?month=${monthStr}`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setBudgets(data.categories || []);
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Error fetching budgets:', error);
    }
  };

  const handleMonthNavigation = (direction) => {
    const newMonth = new Date(selectedMonth);
    if (direction === 'prev') {
      newMonth.setMonth(newMonth.getMonth() - 1);
    } else {
      newMonth.setMonth(newMonth.getMonth() + 1);
    }
    setSelectedMonth(newMonth);
    // Update URL parameter
    const monthStr = `${newMonth.getFullYear()}-${String(newMonth.getMonth() + 1).padStart(2, '0')}`;
    navigate(`/detail/${parentType}?month=${monthStr}`, { replace: true });
  };

  const formatCurrency = (amount) => {
    return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const categoryBudgets = budgets.filter(b => b.parent_type === parentType);

  return (
    <div className="container">
      <div className="summary-container">
        <div className="back-button-container">
          <button onClick={() => {
            const monthStr = `${selectedMonth.getFullYear()}-${String(selectedMonth.getMonth() + 1).padStart(2, '0')}`;
            navigate(`/?month=${monthStr}`);
          }} className="back-btn">← Back to Summary</button>
        </div>
        <div className="month-navigation">
          <button onClick={() => handleMonthNavigation('prev')} className="nav-button">‹</button>
          <span className="month-display">
            {selectedMonth.toLocaleString('default', { month: 'long', year: 'numeric' })}
          </span>
          <button onClick={() => handleMonthNavigation('next')} className="nav-button">›</button>
        </div>
        {categoryBudgets.length === 0 ? (
          <div className="empty-state">
            <p>No {parentType.toLowerCase()} budgets available for this month.</p>
            <p>Budgets are created when you first use the app in a new month.</p>
          </div>
        ) : (
          <div className="summary-cards">
            {categoryBudgets.map(budget => {
              const monthStr = `${selectedMonth.getFullYear()}-${String(selectedMonth.getMonth() + 1).padStart(2, '0')}`;
              return (
              <div key={budget.id} className="summary-card clickable" onClick={() => navigate(`/expenses/${budget.category_id}?month=${monthStr}`)}>
                <h3>{budget.category}</h3>
                <div className="summary-amount">
                  <span className="spent">${formatCurrency(budget.current_spent)}</span>
                  <span className="separator"> / </span>
                  <span className="budget">${formatCurrency(budget.effective_budget)}</span>
                </div>
                <div className={`remaining ${budget.remaining < 0 ? 'over-budget' : ''}`}>
                  {budget.remaining < 0 ? 'Over by' : 'Remaining'}: ${formatCurrency(Math.abs(budget.remaining))}
                </div>
                <div className="progress-bar">
                  <div
                    className={`progress-fill ${budget.remaining < 0 ? 'over-budget' : ''}`}
                    style={{ width: `${Math.min((budget.current_spent / budget.effective_budget) * 100, 100)}%` }}
                  ></div>
                </div>
              </div>
              );
            })}
          </div>
        )}
      </div>

      <footer className="footer">
        <button onClick={handleLogout} className="logout-btn">Logout</button>
      </footer>
    </div>
  );
}

function ExpenseListView({ apiUrl, getAuthHeader, handleLogout, setIsAuthenticated }) {
  const [expenses, setExpenses] = useState([]);
  const [categoryName, setCategoryName] = useState('');
  const [parentType, setParentType] = useState('');
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const { categoryId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Get month from URL parameter, or default to current month
  const monthParam = searchParams.get('month');
  const [selectedMonth, setSelectedMonth] = useState(() => {
    if (monthParam) {
      const [year, month] = monthParam.split('-');
      return new Date(parseInt(year), parseInt(month) - 1, 1);
    }
    return new Date();
  });

  const API_URL = apiUrl;

  useEffect(() => {
    fetchExpenses();
  }, [selectedMonth]);

  const fetchExpenses = async () => {
    try {
      const response = await fetch(`${API_URL}/expenses`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        // Filter expenses for this category and selected month
        const monthStr = `${selectedMonth.getFullYear()}-${String(selectedMonth.getMonth() + 1).padStart(2, '0')}`;
        const filtered = data.filter(exp =>
          exp.category_id === parseInt(categoryId) &&
          exp.expense_date.startsWith(monthStr)
        );
        // Sort by date descending (most recent first)
        const sorted = filtered.sort((a, b) => {
          const dateA = new Date(a.expense_date);
          const dateB = new Date(b.expense_date);
          return dateB - dateA;
        });
        setExpenses(sorted);

        // Get category name and parent type from first expense
        if (filtered.length > 0) {
          setCategoryName(filtered[0].category);
          setParentType(filtered[0].parent_type);
        } else {
          // If no expenses, fetch categories to get the name
          fetchCategoryInfo();
        }
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Error fetching expenses:', error);
    }
  };

  const fetchCategoryInfo = async () => {
    try {
      const response = await fetch(`${API_URL}/categories`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        const category = data.find(cat => cat.id === parseInt(categoryId));
        if (category) {
          setCategoryName(category.name);
          setParentType(category.parent_type);
        }
      }
    } catch (error) {
      console.error('Error fetching category info:', error);
    }
  };

  const handleMonthNavigation = (direction) => {
    const newMonth = new Date(selectedMonth);
    if (direction === 'prev') {
      newMonth.setMonth(newMonth.getMonth() - 1);
    } else {
      newMonth.setMonth(newMonth.getMonth() + 1);
    }
    setSelectedMonth(newMonth);
    // Update URL parameter
    const monthStr = `${newMonth.getFullYear()}-${String(newMonth.getMonth() + 1).padStart(2, '0')}`;
    navigate(`/expenses/${categoryId}?month=${monthStr}`, { replace: true });
  };

  const formatCurrency = (amount) => {
    return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString + 'T00:00:00');
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  const handleDeleteClick = (expenseId) => {
    setDeleteConfirmId(expenseId);
  };

  const handleDeleteConfirm = async (expenseId) => {
    setIsDeleting(true);
    try {
      const response = await fetch(`${API_URL}/expenses/${expenseId}`, {
        method: 'DELETE',
        headers: getAuthHeader()
      });

      if (response.ok) {
        // Remove the expense from the list
        setExpenses(expenses.filter(exp => exp.id !== expenseId));
        setDeleteConfirmId(null);
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      } else if (response.status === 403) {
        alert('You do not have permission to delete this expense');
      } else {
        alert('Error deleting expense');
      }
    } catch (error) {
      console.error('Error deleting expense:', error);
      alert('Error connecting to server');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteConfirmId(null);
  };

  const totalSpent = expenses.reduce((sum, exp) => sum + exp.amount, 0);

  return (
    <div className="container">
      <div className="summary-container">
        <div className="back-button-container">
          <button onClick={() => {
            const monthStr = `${selectedMonth.getFullYear()}-${String(selectedMonth.getMonth() + 1).padStart(2, '0')}`;
            navigate(`/detail/${parentType}?month=${monthStr}`);
          }} className="back-btn">← Back to {parentType} Categories</button>
        </div>

        <div className="month-navigation">
          <button onClick={() => handleMonthNavigation('prev')} className="nav-button">‹</button>
          <span className="month-display">
            {selectedMonth.toLocaleString('default', { month: 'long', year: 'numeric' })}
          </span>
          <button onClick={() => handleMonthNavigation('next')} className="nav-button">›</button>
        </div>

        <div className="expense-summary">
          <div className="expense-total">
            <span className="total-label">Total Spent This Month:</span>
            <span className="total-amount">${formatCurrency(totalSpent)}</span>
          </div>
        </div>

        {expenses.length === 0 ? (
          <p className="no-expenses">No expenses recorded for this category this month.</p>
        ) : (
          <div className="expense-list">
            {expenses.map(expense => (
              <div key={expense.id} className="expense-item">
                <div className="expense-date">{formatDate(expense.expense_date)}</div>
                <div className="expense-details">
                  {expense.description && <div className="expense-description">{expense.description}</div>}
                  <div className="expense-meta">
                    <span className="expense-user">by {expense.created_by}</span>
                  </div>
                </div>
                <div className="expense-amount">${formatCurrency(expense.amount)}</div>
                {deleteConfirmId === expense.id ? (
                  <div className="expense-actions">
                    <button
                      onClick={() => handleDeleteConfirm(expense.id)}
                      className="delete-confirm-btn"
                      disabled={isDeleting}
                    >
                      {isDeleting ? 'Deleting...' : 'Confirm'}
                    </button>
                    <button
                      onClick={handleDeleteCancel}
                      className="delete-cancel-btn"
                      disabled={isDeleting}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => handleDeleteClick(expense.id)}
                    className="delete-btn"
                    title="Delete expense"
                  >
                    Delete
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <footer className="footer">
        <button onClick={handleLogout} className="logout-btn">Logout</button>
      </footer>
    </div>
  );
}

function ExpenseHistoryView({ apiUrl, getAuthHeader, handleLogout, setIsAuthenticated }) {
  const [monthsData, setMonthsData] = useState([]);
  const [monthsBack, setMonthsBack] = useState(2);
  const [isLoading, setIsLoading] = useState(false);
  const [potentialExpenses, setPotentialExpenses] = useState([]);
  const [categories, setCategories] = useState([]);
  const [uploadError, setUploadError] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const navigate = useNavigate();

  const API_URL = apiUrl;

  useEffect(() => {
    fetchExpenseHistory(monthsBack);
    fetchCategories();
  }, []);

  const fetchExpenseHistory = async (months) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${API_URL}/expenses/history?months_back=${months}`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setMonthsData(data.months);
        setMonthsBack(data.months_back);
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Error fetching expense history:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/categories`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setCategories(data);
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_URL}/expenses/parse-csv`, {
        method: 'POST',
        headers: getAuthHeader(),
        body: formData
      });

      if (response.ok) {
        const data = await response.json();

        // Add category_id field to each expense (initially empty)
        const expensesWithCategory = data.expenses.map((exp, index) => ({
          ...exp,
          category_id: '',
          tempId: `temp-${Date.now()}-${index}` // Unique ID for React keys
        }));

        setPotentialExpenses(expensesWithCategory);

        if (data.errors.length > 0) {
          setUploadError(`Parsed ${data.total_parsed} expenses with ${data.total_errors} errors`);
        }
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      } else {
        const errorData = await response.json();
        setUploadError(errorData.error || 'Failed to parse CSV');
      }
    } catch (error) {
      console.error('Error uploading CSV:', error);
      setUploadError('Error connecting to server');
    } finally {
      setIsUploading(false);
      event.target.value = ''; // Reset file input
    }
  };

  const handleCategoryChange = (tempId, categoryId) => {
    setPotentialExpenses(potentialExpenses.map(exp =>
      exp.tempId === tempId ? { ...exp, category_id: categoryId } : exp
    ));
  };

  const handleSaveExpense = async (expense) => {
    if (!expense.category_id) {
      alert('Please select a category before saving');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/expenses/save-csv-expense`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeader()
        },
        body: JSON.stringify({
          date: expense.date,
          description: expense.description,
          amount: expense.amount,
          category_id: parseInt(expense.category_id)
        })
      });

      if (response.ok) {
        // Remove from potential expenses
        setPotentialExpenses(potentialExpenses.filter(exp => exp.tempId !== expense.tempId));
        // Refresh the expense history to show the newly saved expense
        fetchExpenseHistory(monthsBack);
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      } else {
        const errorData = await response.json();
        alert(errorData.error || 'Failed to save expense');
      }
    } catch (error) {
      console.error('Error saving expense:', error);
      alert('Error connecting to server');
    }
  };

  const handleDismissExpense = (tempId) => {
    setPotentialExpenses(potentialExpenses.filter(exp => exp.tempId !== tempId));
  };

  const handleLoadMore = () => {
    const newMonthsBack = monthsBack + 2;
    fetchExpenseHistory(newMonthsBack);
  };

  const formatCurrency = (amount) => {
    return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString + 'T00:00:00');
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  // Merge potential expenses with existing expenses and sort by date
  const getMergedExpenses = () => {
    const allExpenses = [];

    // Add existing expenses
    monthsData.forEach(monthData => {
      monthData.expenses.forEach(expense => {
        allExpenses.push({
          ...expense,
          isPotential: false,
          sortDate: expense.expense_date
        });
      });
    });

    // Add potential expenses
    potentialExpenses.forEach(expense => {
      allExpenses.push({
        ...expense,
        isPotential: true,
        sortDate: expense.date
      });
    });

    // Sort by date descending
    allExpenses.sort((a, b) => {
      return new Date(b.sortDate) - new Date(a.sortDate);
    });

    // Group by month
    const groupedByMonth = {};
    allExpenses.forEach(expense => {
      const monthKey = expense.sortDate.substring(0, 7); // YYYY-MM
      if (!groupedByMonth[monthKey]) {
        groupedByMonth[monthKey] = [];
      }
      groupedByMonth[monthKey].push(expense);
    });

    // Convert to sorted array
    return Object.keys(groupedByMonth)
      .sort((a, b) => b.localeCompare(a))
      .map(monthKey => {
        const date = new Date(monthKey + '-01');
        return {
          month: monthKey,
          month_display: date.toLocaleString('default', { month: 'long', year: 'numeric' }),
          expenses: groupedByMonth[monthKey]
        };
      });
  };

  const mergedMonthsData = potentialExpenses.length > 0 ? getMergedExpenses() : monthsData;

  return (
    <div className="container">
      <div className="summary-container">
        <div className="back-button-container">
          <button onClick={() => navigate('/')} className="back-btn">← Back to Home</button>
        </div>

        <h2 className="history-title">Expense History</h2>

        {/* CSV Upload Section */}
        <div className="csv-upload-container">
          <label htmlFor="csv-upload" className="csv-upload-btn">
            {isUploading ? 'Uploading...' : 'Upload Bank Statement CSV'}
          </label>
          <input
            id="csv-upload"
            type="file"
            accept=".csv"
            onChange={handleFileUpload}
            disabled={isUploading}
            style={{ display: 'none' }}
          />
          {uploadError && <p className="upload-error">{uploadError}</p>}
          {potentialExpenses.length > 0 && (
            <p className="upload-success">
              {potentialExpenses.length} potential expense{potentialExpenses.length !== 1 ? 's' : ''} loaded.
              Review and save below.
            </p>
          )}
        </div>

        {mergedMonthsData.length === 0 && !isLoading ? (
          <p className="no-expenses">No expenses found.</p>
        ) : (
          <div className="history-container">
            {mergedMonthsData.map(monthData => (
              <div key={monthData.month} className="history-month">
                <div className="history-month-header">
                  <h3>{monthData.month_display}</h3>
                  <span className="history-month-total">
                    ${formatCurrency(
                      monthData.expenses
                        .filter(exp => !exp.isPotential)
                        .reduce((sum, exp) => sum + exp.amount, 0)
                    )}
                  </span>
                </div>
                <div className="history-expense-list">
                  {monthData.expenses.map(expense =>
                    expense.isPotential ? (
                      // Potential expense from CSV
                      <div key={expense.tempId} className="history-expense-item potential-expense">
                        <div className="potential-badge">NEW</div>
                        <div className="history-expense-date">{formatDate(expense.date)}</div>
                        <div className="history-expense-details">
                          <div className="history-expense-description">{expense.description}</div>
                          <div className="category-selector">
                            <select
                              value={expense.category_id}
                              onChange={(e) => handleCategoryChange(expense.tempId, e.target.value)}
                              className="potential-category-select"
                            >
                              <option value="">Select category...</option>
                              <optgroup label="Personal">
                                {categories
                                  .filter(cat => cat.parent_type === 'Personal')
                                  .map(cat => (
                                    <option key={cat.id} value={cat.id}>
                                      {cat.name}
                                    </option>
                                  ))}
                              </optgroup>
                              <optgroup label="Shared">
                                {categories
                                  .filter(cat => cat.parent_type === 'Shared')
                                  .map(cat => (
                                    <option key={cat.id} value={cat.id}>
                                      {cat.name}
                                    </option>
                                  ))}
                              </optgroup>
                            </select>
                          </div>
                        </div>
                        <div className="history-expense-amount">${formatCurrency(expense.amount)}</div>
                        <div className="potential-expense-actions">
                          <button
                            onClick={() => handleSaveExpense(expense)}
                            className="save-expense-btn"
                            disabled={!expense.category_id}
                          >
                            Save
                          </button>
                          <button
                            onClick={() => handleDismissExpense(expense.tempId)}
                            className="dismiss-expense-btn"
                          >
                            Dismiss
                          </button>
                        </div>
                      </div>
                    ) : (
                      // Regular existing expense
                      <div key={expense.id} className="history-expense-item">
                        <div className="history-expense-date">{formatDate(expense.expense_date)}</div>
                        <div className="history-expense-details">
                          <div className="history-expense-category">
                            {expense.category}
                            <span className="history-expense-type"> ({expense.parent_type})</span>
                          </div>
                          {expense.description && (
                            <div className="history-expense-description">{expense.description}</div>
                          )}
                          <div className="history-expense-meta">
                            <span className="expense-user">by {expense.created_by}</span>
                          </div>
                        </div>
                        <div className="history-expense-amount">${formatCurrency(expense.amount)}</div>
                      </div>
                    )
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && monthsData.length > 0 && (
          <div className="load-more-container">
            <button onClick={handleLoadMore} className="load-more-btn">
              Load More Months
            </button>
          </div>
        )}

        {isLoading && (
          <div className="loading-indicator">
            <p>Loading...</p>
          </div>
        )}
      </div>

      <footer className="footer">
        <button onClick={handleLogout} className="logout-btn">Logout</button>
      </footer>
    </div>
  );
}

export default App;

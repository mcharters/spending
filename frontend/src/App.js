import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate, useParams } from 'react-router-dom';
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
    </Routes>
  );
}

function MainView({ apiUrl, getAuthHeader, handleLogout, setIsAuthenticated }) {
  const [budgets, setBudgets] = useState([]);
  const [categories, setCategories] = useState([]);
  const [formData, setFormData] = useState({
    amount: '',
    category_id: '',
    expense_date: new Date()
  });
  const navigate = useNavigate();

  const API_URL = apiUrl;

  useEffect(() => {
    fetchBudgets();
    fetchCategories();
  }, []);

  const fetchBudgets = async () => {
    try {
      const response = await fetch(`${API_URL}/budgets`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setBudgets(data);
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Error fetching budgets:', error);
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
        setFormData({ amount: '', category_id: '', expense_date: new Date() });
        fetchBudgets();
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Error creating expense:', error);
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

  const personalTotalBudget = personalBudgets.reduce((sum, b) => sum + b.effective_budget, 0);
  const personalTotalSpent = personalBudgets.reduce((sum, b) => sum + b.current_spent, 0);
  const personalRemaining = personalBudgets.reduce((sum, b) => sum + b.remaining, 0);

  const sharedTotalBudget = sharedBudgets.reduce((sum, b) => sum + b.effective_budget, 0);
  const sharedTotalSpent = sharedBudgets.reduce((sum, b) => sum + b.current_spent, 0);
  const sharedRemaining = sharedBudgets.reduce((sum, b) => sum + b.remaining, 0);

  const formatCurrency = (amount) => {
    return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  return (
    <div className="container">
      <div className="header">
        <h1>Spending Tracker</h1>
        <button onClick={handleLogout} className="logout-btn">Logout</button>
      </div>

      <div className="form-container">
        <h2>Add New Expense</h2>
        <form onSubmit={handleSubmit}>
          <div className="date-picker-container">
            <label>Select Date</label>
            <DatePicker
              selected={formData.expense_date}
              onChange={(date) => setFormData({ ...formData, expense_date: date })}
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
                    onClick={decreaseMonth}
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
                    onClick={increaseMonth}
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
          <button type="submit">Add Expense</button>
        </form>
      </div>

      <div className="summary-container">
        <h2>Current Month Summary</h2>
        <div className="summary-cards">
          <div className="summary-card clickable" onClick={() => navigate('/detail/Personal')}>
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

          <div className="summary-card clickable" onClick={() => navigate('/detail/Shared')}>
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
        </div>
      </div>
    </div>
  );
}

function DetailView({ apiUrl, getAuthHeader, handleLogout, setIsAuthenticated }) {
  const [budgets, setBudgets] = useState([]);
  const { parentType } = useParams();
  const navigate = useNavigate();

  const API_URL = apiUrl;

  useEffect(() => {
    fetchBudgets();
  }, []);

  const fetchBudgets = async () => {
    try {
      const response = await fetch(`${API_URL}/budgets`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setBudgets(data);
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Error fetching budgets:', error);
    }
  };

  const formatCurrency = (amount) => {
    return amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const categoryBudgets = budgets.filter(b => b.parent_type === parentType);

  return (
    <div className="container">
      <div className="header">
        <h1>Spending Tracker</h1>
        <button onClick={handleLogout} className="logout-btn">Logout</button>
      </div>

      <div className="summary-container">
        <div className="back-button-container">
          <button onClick={() => navigate('/')} className="back-btn">← Back to Summary</button>
        </div>
        <h2>{parentType} Categories</h2>
        <div className="summary-cards">
          {categoryBudgets.map(budget => (
            <div key={budget.id} className="summary-card">
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
          ))}
        </div>
      </div>
    </div>
  );
}

export default App;

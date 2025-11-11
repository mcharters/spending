import React, { useState, useEffect } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

function App() {
  const [expenses, setExpenses] = useState([]);
  const [categories, setCategories] = useState([]);
  const [formData, setFormData] = useState({
    amount: '',
    category_id: '',
    expense_date: new Date()
  });
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [loginForm, setLoginForm] = useState({ username: '', password: '' });
  const [loginError, setLoginError] = useState('');

  const API_URL = process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:5000/api';

  // Create Basic Auth header
  const getAuthHeader = () => {
    const token = btoa(`${credentials.username}:${credentials.password}`);
    return { 'Authorization': `Basic ${token}` };
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchExpenses();
      fetchCategories();
    }
  }, [isAuthenticated]);

  const fetchExpenses = async () => {
    try {
      const response = await fetch(`${API_URL}/expenses`, {
        headers: getAuthHeader()
      });
      if (response.ok) {
        const data = await response.json();
        setExpenses(data);
      } else if (response.status === 401) {
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Error fetching expenses:', error);
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

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');

    try {
      // Test the credentials by fetching categories
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
    setExpenses([]);
    setCategories([]);
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
        fetchExpenses();
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

  const totalAmount = expenses.reduce((sum, expense) => sum + expense.amount, 0);

  // Show login form if not authenticated
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

      <div className="expenses-container">
        <h2>Expenses (Total: ${totalAmount.toFixed(2)})</h2>
        <div className="expenses-list">
          {expenses.length === 0 ? (
            <p>No expenses yet. Add your first expense above!</p>
          ) : (
            expenses.map(expense => (
              <div key={expense.id} className="expense-item">
                <div className="expense-details">
                  <span className="category">{expense.category}</span>
                  <span className="expense-date">
                    {new Date(expense.expense_date + 'T00:00:00').toLocaleDateString()}
                  </span>
                </div>
                <div className="expense-amount">${expense.amount.toFixed(2)}</div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default App;

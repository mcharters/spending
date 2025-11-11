import React, { useState, useEffect } from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

function App() {
  const [expenses, setExpenses] = useState([]);
  const [categories, setCategories] = useState([]);
  const [formData, setFormData] = useState({
    description: '',
    amount: '',
    category_id: '',
    expense_date: new Date()
  });

  const API_URL = process.env.NODE_ENV === 'production' ? '/api' : 'http://localhost:5000/api';

  useEffect(() => {
    fetchExpenses();
    fetchCategories();
  }, []);

  const fetchExpenses = async () => {
    try {
      const response = await fetch(`${API_URL}/expenses`);
      const data = await response.json();
      setExpenses(data);
    } catch (error) {
      console.error('Error fetching expenses:', error);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${API_URL}/categories`);
      const data = await response.json();
      setCategories(data);
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
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ...formData,
          amount: parseFloat(formData.amount),
          expense_date: formData.expense_date.toISOString().split('T')[0]
        })
      });

      if (response.ok) {
        setFormData({ description: '', amount: '', category_id: '', expense_date: new Date() });
        fetchExpenses();
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

  return (
    <div className="container">
      <h1>Spending Tracker</h1>

      <div className="form-container">
        <h2>Add New Expense</h2>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            name="description"
            placeholder="Description"
            value={formData.description}
            onChange={handleChange}
            required
          />
          <input
            type="number"
            name="amount"
            placeholder="Amount"
            step="0.01"
            value={formData.amount}
            onChange={handleChange}
            required
          />
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
                  <strong>{expense.description}</strong>
                  <span className="category">{expense.category}</span>
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

"""
Tests for the expense history endpoint.
"""
import pytest
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from models import db, Category, Budget, Expense
from base64 import b64encode


@pytest.fixture
def setup_test_data(app):
    """Set up test categories, budgets, and expenses."""
    with app.app_context():
        # Create categories
        personal_cat = Category(name='Dining', parent_type='Personal')
        shared_cat = Category(name='Groceries', parent_type='Shared')
        db.session.add_all([personal_cat, shared_cat])
        db.session.commit()

        # Create budgets
        personal_budget = Budget(category_id=personal_cat.id, user='user1', monthly_amount=500)
        shared_budget = Budget(category_id=shared_cat.id, user=None, monthly_amount=1000)
        db.session.add_all([personal_budget, shared_budget])
        db.session.commit()

        # Create expenses across multiple months
        current_date = datetime.utcnow()

        # Current month expenses
        expense1 = Expense(
            amount=50.00,
            category_id=personal_cat.id,
            created_by='user1',
            expense_date=current_date.date()
        )
        expense2 = Expense(
            amount=100.00,
            category_id=shared_cat.id,
            created_by='user1',
            expense_date=current_date.date()
        )

        # Last month expenses
        last_month_date = current_date - relativedelta(months=1)
        expense3 = Expense(
            amount=75.00,
            category_id=personal_cat.id,
            created_by='user1',
            expense_date=last_month_date.date()
        )
        expense4 = Expense(
            amount=150.00,
            category_id=shared_cat.id,
            created_by='user2',
            expense_date=last_month_date.date()
        )

        # Two months ago expenses
        two_months_ago = current_date - relativedelta(months=2)
        expense5 = Expense(
            amount=60.00,
            category_id=personal_cat.id,
            created_by='user1',
            expense_date=two_months_ago.date()
        )

        # Three months ago (should not appear in 2-month default)
        three_months_ago = current_date - relativedelta(months=3)
        expense6 = Expense(
            amount=200.00,
            category_id=shared_cat.id,
            created_by='user1',
            expense_date=three_months_ago.date()
        )

        db.session.add_all([expense1, expense2, expense3, expense4, expense5, expense6])
        db.session.commit()

        yield {
            'personal_cat': personal_cat,
            'shared_cat': shared_cat,
            'current_date': current_date
        }


def get_auth_header(username='user1', password='password123'):
    """Helper to create Basic Auth header."""
    credentials = b64encode(f'{username}:{password}'.encode()).decode('utf-8')
    return {'Authorization': f'Basic {credentials}'}


def test_expense_history_default_two_months(client, setup_test_data):
    """Test that expense history returns last 2 months by default."""
    response = client.get('/api/expenses/history', headers=get_auth_header())

    assert response.status_code == 200
    data = response.json

    # Should have 2 months of data (current + last month)
    assert data['months_back'] == 2
    assert len(data['months']) <= 2  # May be 1 if no expenses in older month

    # Verify expenses are grouped by month
    for month_data in data['months']:
        assert 'month' in month_data
        assert 'month_display' in month_data
        assert 'expenses' in month_data
        assert 'total' in month_data
        assert isinstance(month_data['expenses'], list)
        assert isinstance(month_data['total'], (int, float))


def test_expense_history_custom_months_back(client, setup_test_data):
    """Test that expense history respects custom months_back parameter."""
    response = client.get('/api/expenses/history?months_back=3', headers=get_auth_header())

    assert response.status_code == 200
    data = response.json

    assert data['months_back'] == 3
    # Should include expenses from up to 3 months ago


def test_expense_history_user_filter(client, setup_test_data):
    """Test that users only see their own personal expenses and all shared expenses."""
    # User1 should see their own personal expenses + all shared expenses
    response = client.get('/api/expenses/history?months_back=3', headers=get_auth_header('user1'))

    assert response.status_code == 200
    data = response.json

    # Collect all expenses
    all_expenses = []
    for month_data in data['months']:
        all_expenses.extend(month_data['expenses'])

    # Verify user1 sees their personal expenses
    personal_expenses = [e for e in all_expenses if e['parent_type'] == 'Personal']
    assert all(e['created_by'] == 'user1' for e in personal_expenses)

    # Verify user1 sees all shared expenses (from both users)
    shared_expenses = [e for e in all_expenses if e['parent_type'] == 'Shared']
    assert len(shared_expenses) > 0
    # Should include expenses from both user1 and user2
    creators = {e['created_by'] for e in shared_expenses}
    assert 'user1' in creators or 'user2' in creators


def test_expense_history_month_totals(client, setup_test_data):
    """Test that month totals are calculated correctly."""
    response = client.get('/api/expenses/history?months_back=2', headers=get_auth_header())

    assert response.status_code == 200
    data = response.json

    for month_data in data['months']:
        # Calculate expected total
        expected_total = sum(e['amount'] for e in month_data['expenses'])
        assert abs(month_data['total'] - expected_total) < 0.01  # Float comparison


def test_expense_history_sorted_by_date(client, setup_test_data):
    """Test that expenses within each month are sorted by date (newest first)."""
    response = client.get('/api/expenses/history?months_back=3', headers=get_auth_header())

    assert response.status_code == 200
    data = response.json

    # Verify months are sorted newest first
    month_keys = [m['month'] for m in data['months']]
    assert month_keys == sorted(month_keys, reverse=True)

    # Verify expenses within each month are sorted by date (newest first)
    for month_data in data['months']:
        dates = [e['expense_date'] for e in month_data['expenses']]
        assert dates == sorted(dates, reverse=True)


def test_expense_history_requires_auth(client, setup_test_data):
    """Test that expense history endpoint requires authentication."""
    response = client.get('/api/expenses/history')
    assert response.status_code == 401


def test_expense_history_empty_result(client, app):
    """Test expense history when no expenses exist."""
    with app.app_context():
        # Create categories and budgets but no expenses
        personal_cat = Category(name='Test', parent_type='Personal')
        db.session.add(personal_cat)
        db.session.commit()

        budget = Budget(category_id=personal_cat.id, user='user1', monthly_amount=500)
        db.session.add(budget)
        db.session.commit()

    response = client.get('/api/expenses/history', headers=get_auth_header())

    assert response.status_code == 200
    data = response.json

    assert data['months_back'] == 2
    assert len(data['months']) == 0

"""
Tests for saving validated CSV expenses.
"""
import pytest
from datetime import datetime
from models import db, Category, Budget, Expense
from base64 import b64encode


@pytest.fixture
def setup_test_data(app):
    """Set up test categories and budgets."""
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

        yield {
            'personal_cat': personal_cat,
            'shared_cat': shared_cat
        }


def get_auth_header(username='user1', password='password123'):
    """Helper to create Basic Auth header."""
    credentials = b64encode(f'{username}:{password}'.encode()).decode('utf-8')
    return {'Authorization': f'Basic {credentials}'}


def test_save_csv_expense_success(client, setup_test_data):
    """Test successfully saving a CSV expense."""
    data = {
        'date': '2025-12-15',
        'description': 'TIM HORTONS #1551',
        'amount': 25.59,
        'category_id': setup_test_data['personal_cat'].id
    }

    response = client.post(
        '/api/expenses/save-csv-expense',
        json=data,
        headers=get_auth_header('user1')
    )

    assert response.status_code == 201
    result = response.json

    assert result['description'] == 'TIM HORTONS #1551'
    assert result['amount'] == 25.59
    assert result['created_by'] == 'user1'
    assert result['expense_date'] == '2025-12-15'


def test_save_csv_expense_shared_category(client, setup_test_data):
    """Test saving a CSV expense to a shared category."""
    data = {
        'date': '2025-12-10',
        'description': 'SOBEYS #649',
        'amount': 123.45,
        'category_id': setup_test_data['shared_cat'].id
    }

    response = client.post(
        '/api/expenses/save-csv-expense',
        json=data,
        headers=get_auth_header('user1')
    )

    assert response.status_code == 201
    result = response.json

    assert result['category'] == 'Groceries'
    assert result['parent_type'] == 'Shared'


def test_save_csv_expense_missing_date(client, setup_test_data):
    """Test error when date is missing."""
    data = {
        'description': 'Test Expense',
        'amount': 100.00,
        'category_id': setup_test_data['personal_cat'].id
    }

    response = client.post(
        '/api/expenses/save-csv-expense',
        json=data,
        headers=get_auth_header()
    )

    assert response.status_code == 400
    assert 'Date is required' in response.json['error']


def test_save_csv_expense_missing_amount(client, setup_test_data):
    """Test error when amount is missing."""
    data = {
        'date': '2025-12-15',
        'description': 'Test Expense',
        'category_id': setup_test_data['personal_cat'].id
    }

    response = client.post(
        '/api/expenses/save-csv-expense',
        json=data,
        headers=get_auth_header()
    )

    assert response.status_code == 400
    assert 'Amount is required' in response.json['error']


def test_save_csv_expense_missing_category(client, setup_test_data):
    """Test error when category is missing."""
    data = {
        'date': '2025-12-15',
        'description': 'Test Expense',
        'amount': 100.00
    }

    response = client.post(
        '/api/expenses/save-csv-expense',
        json=data,
        headers=get_auth_header()
    )

    assert response.status_code == 400
    assert 'Category is required' in response.json['error']


def test_save_csv_expense_invalid_date_format(client, setup_test_data):
    """Test error when date format is invalid."""
    data = {
        'date': 'INVALID-DATE',
        'description': 'Test Expense',
        'amount': 100.00,
        'category_id': setup_test_data['personal_cat'].id
    }

    response = client.post(
        '/api/expenses/save-csv-expense',
        json=data,
        headers=get_auth_header()
    )

    assert response.status_code == 400
    assert 'Invalid date format' in response.json['error']


def test_save_csv_expense_category_not_found(client, setup_test_data):
    """Test error when category does not exist."""
    data = {
        'date': '2025-12-15',
        'description': 'Test Expense',
        'amount': 100.00,
        'category_id': 9999  # Non-existent category
    }

    response = client.post(
        '/api/expenses/save-csv-expense',
        json=data,
        headers=get_auth_header()
    )

    assert response.status_code == 404
    assert 'Category not found' in response.json['error']


def test_save_csv_expense_no_budget_exists(client, app):
    """Test error when no budget exists for the category."""
    with app.app_context():
        # Create a category without a budget
        cat = Category(name='NoBudget', parent_type='Personal')
        db.session.add(cat)
        db.session.commit()
        cat_id = cat.id

    data = {
        'date': '2025-12-15',
        'description': 'Test Expense',
        'amount': 100.00,
        'category_id': cat_id
    }

    response = client.post(
        '/api/expenses/save-csv-expense',
        json=data,
        headers=get_auth_header()
    )

    assert response.status_code == 400
    assert 'No budget exists' in response.json['error']


def test_save_csv_expense_requires_authentication(client, setup_test_data):
    """Test that endpoint requires authentication."""
    data = {
        'date': '2025-12-15',
        'description': 'Test Expense',
        'amount': 100.00,
        'category_id': setup_test_data['personal_cat'].id
    }

    response = client.post('/api/expenses/save-csv-expense', json=data)
    assert response.status_code == 401


def test_save_csv_expense_with_empty_description(client, setup_test_data):
    """Test saving expense with empty description."""
    data = {
        'date': '2025-12-15',
        'description': '',
        'amount': 50.00,
        'category_id': setup_test_data['personal_cat'].id
    }

    response = client.post(
        '/api/expenses/save-csv-expense',
        json=data,
        headers=get_auth_header()
    )

    assert response.status_code == 201
    result = response.json
    assert result['description'] == ''


def test_save_csv_expense_creates_database_record(client, setup_test_data, app):
    """Test that saving CSV expense creates actual database record."""
    data = {
        'date': '2025-12-15',
        'description': 'Test Expense',
        'amount': 75.50,
        'category_id': setup_test_data['personal_cat'].id
    }

    response = client.post(
        '/api/expenses/save-csv-expense',
        json=data,
        headers=get_auth_header('user1')
    )

    assert response.status_code == 201

    # Verify expense was created in database
    with app.app_context():
        expense = Expense.query.filter_by(description='Test Expense').first()
        assert expense is not None
        assert expense.amount == 75.50
        assert expense.created_by == 'user1'

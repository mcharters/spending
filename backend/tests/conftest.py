"""
Pytest configuration and fixtures for testing the spending tracker app.
"""
import pytest
import os
from datetime import datetime
from app import app as flask_app
from models import db, Category, Budget, Expense


@pytest.fixture
def app():
    """Create and configure a test Flask application.

    IMPORTANT: Tests use an in-memory SQLite database (:memory:) that is
    completely isolated from the dev server database (backend/data/database.db).
    Each test gets a fresh database that is created and destroyed automatically.
    """
    # Set test configuration
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',  # In-memory test database (isolated from dev)
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'WTF_CSRF_ENABLED': False,
    })

    # Mock authentication for testing
    from app import auth

    @auth.verify_password
    def verify_password_test(username, password):
        # Accept test credentials
        if username in ['user1', 'user2'] and password == 'password123':
            return True
        return False

    # Create tables
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""
    return app.test_client()


@pytest.fixture
def auth_headers():
    """Create Basic Auth headers for test users."""
    import base64

    def _auth_headers(username='user1', password='password123'):
        credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
        return {'Authorization': f'Basic {credentials}'}

    return _auth_headers


@pytest.fixture
def sample_categories(app):
    """Create sample categories for testing."""
    with app.app_context():
        categories = [
            Category(name='Beauty', parent_type='Personal'),
            Category(name='Clothing', parent_type='Personal'),
            Category(name='Groceries', parent_type='Shared'),
            Category(name='Car', parent_type='Shared'),
        ]
        db.session.add_all(categories)
        db.session.commit()

        # Return category IDs
        return {cat.name: cat.id for cat in categories}


@pytest.fixture
def sample_budgets(app, sample_categories):
    """Create sample budgets for testing."""
    with app.app_context():
        current_month = datetime.utcnow().strftime('%Y-%m')

        budgets = [
            Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100,
                cumulative_balance=0,
                last_updated_month=current_month
            ),
            Budget(
                category_id=sample_categories['Clothing'],
                user='user1',
                monthly_amount=150,
                cumulative_balance=0,
                last_updated_month=current_month
            ),
            Budget(
                category_id=sample_categories['Groceries'],
                user=None,  # Shared
                monthly_amount=1200,
                cumulative_balance=0,
                last_updated_month=current_month
            ),
        ]
        db.session.add_all(budgets)
        db.session.commit()

        return budgets


@pytest.fixture
def sample_expenses(app, sample_categories):
    """Create sample expenses for testing."""
    with app.app_context():
        expenses = [
            Expense(
                amount=50.00,
                category_id=sample_categories['Beauty'],
                created_by='user1',
                expense_date=datetime(2025, 1, 15).date(),
                description='Test expense 1'
            ),
            Expense(
                amount=75.50,
                category_id=sample_categories['Groceries'],
                created_by='user1',
                expense_date=datetime(2025, 1, 20).date(),
                description='Test expense 2'
            ),
            Expense(
                amount=200.00,
                category_id=sample_categories['Groceries'],
                created_by='user2',
                expense_date=datetime(2025, 1, 25).date(),
                description='Test expense 3'
            ),
        ]
        db.session.add_all(expenses)
        db.session.commit()

        return expenses

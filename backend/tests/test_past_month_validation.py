"""
Tests for past month expense validation.

These tests verify that the application correctly:
- Allows expenses for current and future months
- Rejects expenses for past months when no budget exists
- Allows expenses for past months when a budget exists
"""
import pytest
from datetime import datetime
from freezegun import freeze_time
from models import db, Budget, Category


@freeze_time("2025-02-15")
class TestPastMonthValidation:
    """Test expense validation for past months without budgets."""

    @pytest.mark.integration
    def test_allow_expense_for_current_month(self, client, auth_headers, sample_categories):
        """Test that expenses for current month are allowed."""
        # Create budget for current month (February)
        with client.application.app_context():
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100,
                cumulative_balance=0,
                last_updated_month='2025-02'
            )
            db.session.add(budget)
            db.session.commit()

        response = client.post(
            '/api/expenses',
            json={
                'amount': 50.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-02-15'
            },
            headers=auth_headers()
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['amount'] == 50.00

    @pytest.mark.integration
    def test_allow_expense_for_future_month(self, client, auth_headers, sample_categories):
        """Test that expenses for future months are allowed."""
        response = client.post(
            '/api/expenses',
            json={
                'amount': 75.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-03-20'
            },
            headers=auth_headers()
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['amount'] == 75.00
        assert data['expense_date'] == '2025-03-20'

    @pytest.mark.integration
    def test_reject_expense_for_past_month_without_budget(self, client, auth_headers, sample_categories):
        """Test that expenses for past months without budgets are rejected."""
        # No budget exists for January
        response = client.post(
            '/api/expenses',
            json={
                'amount': 100.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-10'
            },
            headers=auth_headers()
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Cannot add expense to past month' in data['error']
        assert '2025-01' in data['error']

    @pytest.mark.integration
    def test_allow_expense_for_past_month_with_budget(self, client, auth_headers, sample_categories):
        """Test that expenses for past months WITH budgets are allowed."""
        # Create budget for January
        with client.application.app_context():
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100,
                cumulative_balance=0,
                last_updated_month='2025-01'
            )
            db.session.add(budget)
            db.session.commit()

        response = client.post(
            '/api/expenses',
            json={
                'amount': 60.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-20'
            },
            headers=auth_headers()
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['amount'] == 60.00
        assert data['expense_date'] == '2025-01-20'

    @pytest.mark.integration
    def test_reject_expense_for_shared_category_past_month_without_budget(self, client, auth_headers, sample_categories):
        """Test that shared category expenses are also validated."""
        # No budget exists for Groceries in January
        response = client.post(
            '/api/expenses',
            json={
                'amount': 200.00,
                'category_id': sample_categories['Groceries'],
                'expense_date': '2025-01-15'
            },
            headers=auth_headers()
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Cannot add expense to past month' in data['error']

    @pytest.mark.integration
    def test_allow_expense_for_shared_category_past_month_with_budget(self, client, auth_headers, sample_categories):
        """Test that shared category expenses work when budget exists."""
        # Create budget for Groceries in January
        with client.application.app_context():
            budget = Budget(
                category_id=sample_categories['Groceries'],
                user=None,  # Shared
                monthly_amount=1200,
                cumulative_balance=0,
                last_updated_month='2025-01'
            )
            db.session.add(budget)
            db.session.commit()

        response = client.post(
            '/api/expenses',
            json={
                'amount': 150.00,
                'category_id': sample_categories['Groceries'],
                'expense_date': '2025-01-25'
            },
            headers=auth_headers()
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['amount'] == 150.00

    @pytest.mark.integration
    def test_invalid_category_returns_404(self, client, auth_headers):
        """Test that invalid category ID returns 404."""
        response = client.post(
            '/api/expenses',
            json={
                'amount': 50.00,
                'category_id': 9999,
                'expense_date': '2025-02-15'
            },
            headers=auth_headers()
        )

        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'Category not found' in data['error']


@freeze_time("2025-03-15")
class TestBudgetLastUpdatedMonthValidation:
    """Test validation for budgets that haven't been updated to intermediate months."""

    @pytest.mark.integration
    def test_reject_expense_for_intermediate_past_month(self, client, auth_headers, sample_categories):
        """Test that expenses are rejected for past months between last_updated and current."""
        # Budget last updated in January, now in March, trying to add February expense
        with client.application.app_context():
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100,
                cumulative_balance=0,
                last_updated_month='2025-01'
            )
            db.session.add(budget)
            db.session.commit()

        response = client.post(
            '/api/expenses',
            json={
                'amount': 50.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-02-10'
            },
            headers=auth_headers()
        )

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'Cannot add expense to past month' in data['error']
        assert '2025-02' in data['error']

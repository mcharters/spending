"""
Tests for date filtering and month boundary scenarios.

These tests verify that the application correctly handles:
- Filtering expenses by date ranges
- Month transitions in budget calculations
- Future-dated expenses
- Historical data queries
"""
import pytest
from datetime import datetime, timedelta
from freezegun import freeze_time
from models import db, Expense, Budget, Category


class TestExpenseDateFiltering:
    """Test expense filtering by date ranges."""

    @pytest.mark.unit
    def test_create_expense_with_custom_date(self, app, client, auth_headers, sample_categories):
        """Test creating an expense with a specific date."""
        expense_date = '2025-02-15'

        # Create budget for February to allow the expense
        with app.app_context():
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
                'amount': 100.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': expense_date
            },
            headers=auth_headers()
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['expense_date'] == expense_date
        assert data['amount'] == 100.00

    @pytest.mark.unit
    def test_create_expense_future_date(self, client, auth_headers, sample_categories):
        """Test creating an expense with a future date (e.g., next month)."""
        future_date = (datetime.utcnow() + timedelta(days=40)).strftime('%Y-%m-%d')

        response = client.post(
            '/api/expenses',
            json={
                'amount': 250.00,
                'category_id': sample_categories['Clothing'],
                'expense_date': future_date
            },
            headers=auth_headers()
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['expense_date'] == future_date

    @pytest.mark.unit
    def test_create_expense_past_date(self, app, client, auth_headers, sample_categories):
        """Test creating an expense with a past date (e.g., last month)."""
        past_date = (datetime.utcnow() - timedelta(days=40)).strftime('%Y-%m-%d')
        past_month = (datetime.utcnow() - timedelta(days=40)).strftime('%Y-%m')

        # Create budget for past month to allow the expense
        with app.app_context():
            budget = Budget(
                category_id=sample_categories['Groceries'],
                user=None,  # Shared category
                monthly_amount=1200,
                cumulative_balance=0,
                last_updated_month=past_month
            )
            db.session.add(budget)
            db.session.commit()

        response = client.post(
            '/api/expenses',
            json={
                'amount': 75.50,
                'category_id': sample_categories['Groceries'],
                'expense_date': past_date
            },
            headers=auth_headers()
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['expense_date'] == past_date


@freeze_time("2025-01-15")
class TestBudgetMonthTransitions:
    """Test budget calculations across month boundaries."""

    @pytest.mark.integration
    def test_budget_current_month_calculation(self, app, client, auth_headers, sample_budgets, sample_categories):
        """Test that current month spending is calculated correctly."""
        # Add expenses for current month (January 2025)
        client.post(
            '/api/expenses',
            json={
                'amount': 50.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-10'
            },
            headers=auth_headers()
        )

        response = client.get('/api/budgets', headers=auth_headers())
        assert response.status_code == 200

        budgets = response.get_json()
        beauty_budget = next(b for b in budgets if b['category'] == 'Beauty')

        assert beauty_budget['current_spent'] == 50.00
        assert beauty_budget['monthly_amount'] == 100.00
        assert beauty_budget['remaining'] == 50.00

    @pytest.mark.integration
    def test_budget_excludes_future_expenses(self, app, client, auth_headers, sample_budgets, sample_categories):
        """Test that future-dated expenses don't count toward current month's budget."""
        # Add expense for future month (February 2025)
        client.post(
            '/api/expenses',
            json={
                'amount': 75.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-02-15'
            },
            headers=auth_headers()
        )

        # Add expense for current month
        client.post(
            '/api/expenses',
            json={
                'amount': 25.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-15'
            },
            headers=auth_headers()
        )

        response = client.get('/api/budgets', headers=auth_headers())
        budgets = response.get_json()
        beauty_budget = next(b for b in budgets if b['category'] == 'Beauty')

        # Only current month's expense should count
        assert beauty_budget['current_spent'] == 25.00

    @pytest.mark.integration
    def test_budget_excludes_past_month_expenses(self, app, client, auth_headers, sample_budgets, sample_categories):
        """Test that past month expenses don't count toward current month's budget."""
        # Add expense for past month (December 2024)
        client.post(
            '/api/expenses',
            json={
                'amount': 100.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2024-12-20'
            },
            headers=auth_headers()
        )

        # Add expense for current month
        client.post(
            '/api/expenses',
            json={
                'amount': 30.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-10'
            },
            headers=auth_headers()
        )

        response = client.get('/api/budgets', headers=auth_headers())
        budgets = response.get_json()
        beauty_budget = next(b for b in budgets if b['category'] == 'Beauty')

        # Only current month's expense should count
        assert beauty_budget['current_spent'] == 30.00


@freeze_time("2025-01-31")
class TestMonthRollover:
    """Test budget rollover when transitioning to a new month."""

    @pytest.mark.integration
    def test_budget_rollover_with_surplus(self, app, client, auth_headers, sample_budgets, sample_categories):
        """Test that unspent budget rolls over to next month."""
        # Spend less than budget in January
        client.post(
            '/api/expenses',
            json={
                'amount': 40.00,  # Budget is 100, so 60 surplus
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-15'
            },
            headers=auth_headers()
        )

        # Check budget in January
        response = client.get('/api/budgets', headers=auth_headers())
        budgets = response.get_json()
        beauty_budget = next(b for b in budgets if b['category'] == 'Beauty')
        assert beauty_budget['remaining'] == 60.00

        # Move to February
        with freeze_time("2025-02-15"):
            response = client.get('/api/budgets', headers=auth_headers())
            budgets = response.get_json()
            beauty_budget = next(b for b in budgets if b['category'] == 'Beauty')

            # Effective budget should be monthly_amount + cumulative_balance
            # cumulative_balance should be 60 (100 budget - 40 spent)
            assert beauty_budget['cumulative_balance'] == 60.00
            assert beauty_budget['effective_budget'] == 160.00  # 100 + 60

    @pytest.mark.integration
    def test_budget_rollover_with_overspending(self, app, client, auth_headers, sample_budgets, sample_categories):
        """Test that overspending reduces next month's budget."""
        # Update budget to have last_updated_month in January
        with app.app_context():
            budget = Budget.query.filter_by(category_id=sample_categories['Beauty']).first()
            budget.last_updated_month = '2025-01'
            db.session.commit()

        # Spend more than budget in January
        client.post(
            '/api/expenses',
            json={
                'amount': 150.00,  # Budget is 100, so -50 deficit
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-15'
            },
            headers=auth_headers()
        )

        # Move to February
        with freeze_time("2025-02-15"):
            response = client.get('/api/budgets', headers=auth_headers())
            budgets = response.get_json()
            beauty_budget = next(b for b in budgets if b['category'] == 'Beauty')

            # cumulative_balance should be -50 (100 budget - 150 spent)
            assert beauty_budget['cumulative_balance'] == -50.00
            assert beauty_budget['effective_budget'] == 50.00  # 100 + (-50)

    @pytest.mark.integration
    def test_budget_rollover_multiple_months(self, app, client, auth_headers, sample_budgets, sample_categories):
        """Test budget rollover across multiple months."""
        # Update budget to have last_updated_month in January
        with app.app_context():
            budget = Budget.query.filter_by(category_id=sample_categories['Beauty']).first()
            budget.last_updated_month = '2025-01'
            db.session.commit()

        # January: Spend 70 (30 surplus)
        with freeze_time("2025-01-15"):
            client.post(
                '/api/expenses',
                json={
                    'amount': 70.00,
                    'category_id': sample_categories['Beauty'],
                    'expense_date': '2025-01-15'
                },
                headers=auth_headers()
            )

        # February: Spend 80 (50 surplus total: 30 + 100 - 80)
        with freeze_time("2025-02-15"):
            client.post(
                '/api/expenses',
                json={
                    'amount': 80.00,
                    'category_id': sample_categories['Beauty'],
                    'expense_date': '2025-02-15'
                },
                headers=auth_headers()
            )

        # March: Check cumulative balance
        with freeze_time("2025-03-15"):
            response = client.get('/api/budgets', headers=auth_headers())
            budgets = response.get_json()
            beauty_budget = next(b for b in budgets if b['category'] == 'Beauty')

            # Jan: 100 - 70 = +30
            # Feb: 30 + 100 - 80 = +50
            assert beauty_budget['cumulative_balance'] == 50.00
            assert beauty_budget['effective_budget'] == 150.00  # 100 + 50


class TestExpenseRetrieval:
    """Test retrieving expenses with date considerations."""

    @pytest.mark.unit
    def test_get_all_expenses_includes_all_dates(self, client, auth_headers, sample_expenses):
        """Test that GET /api/expenses returns expenses regardless of date."""
        response = client.get('/api/expenses', headers=auth_headers())

        assert response.status_code == 200
        expenses = response.get_json()

        # Should include all expenses visible to user1
        assert len(expenses) >= 2  # User1's expense + shared expenses

    @pytest.mark.unit
    def test_shared_expenses_visible_to_all_users(self, client, auth_headers, sample_expenses):
        """Test that shared category expenses are visible to all users."""
        # User1 makes request
        response = client.get('/api/expenses', headers=auth_headers('user1'))
        user1_expenses = response.get_json()

        # Should see shared expenses (Groceries) from both users
        groceries_expenses = [e for e in user1_expenses if e['category'] == 'Groceries']
        assert len(groceries_expenses) >= 2  # Both user1 and user2 groceries

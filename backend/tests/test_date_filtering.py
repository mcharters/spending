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
from models import db, Expense, Budget, Category, MonthlyBudgetSnapshot


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
                monthly_amount=100
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
    def test_create_expense_future_date(self, app, client, auth_headers, sample_categories):
        """Test creating an expense with a future date (e.g., next month)."""
        future_date = (datetime.utcnow() + timedelta(days=40)).strftime('%Y-%m-%d')

        # Need to create a budget first (app requires budget to exist for any expense)
        with app.app_context():
            budget = Budget(
                category_id=sample_categories['Clothing'],
                user='user1',
                monthly_amount=150
            )
            db.session.add(budget)
            db.session.commit()

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
                monthly_amount=1200
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

        data = response.get_json()
        budgets = data['categories']
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
        data = response.get_json()
        budgets = data['categories']
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
        data = response.get_json()
        budgets = data['categories']
        beauty_budget = next(b for b in budgets if b['category'] == 'Beauty')

        # Only current month's expense should count
        assert beauty_budget['current_spent'] == 30.00


@freeze_time("2025-01-31")
class TestMonthRollover:
    """Test budget rollover when transitioning to a new month."""

    @pytest.mark.integration
    def test_budget_rollover_with_surplus(self, app, client, auth_headers, sample_budgets, sample_categories):
        """Test that unspent budget rolls over to next month."""
        # Create a MonthlyBudgetSnapshot for January with surplus
        with app.app_context():
            snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01',
                monthly_amount=100,
                carried_surplus=0,
                carried_deficit=0,
                actual_spent=40.00  # Spent 40, so 60 surplus
            )
            db.session.add(snapshot)
            db.session.commit()

        # Move to February and check budget
        with freeze_time("2025-02-15"):
            response = client.get('/api/budgets', headers=auth_headers())
            data = response.get_json()
            budgets = data['categories']
            beauty_budget = next(b for b in budgets if b['category'] == 'Beauty')

            # Effective budget should include the surplus from January
            # 60 surplus should increase effective budget
            # API doesn't return carried_surplus, but effective_budget reflects it
            assert beauty_budget['effective_budget'] == 160.00  # 100 + 60 surplus
            assert beauty_budget['current_spent'] == 0  # No spending in Feb yet
            assert beauty_budget['remaining'] == 160.00

    @pytest.mark.integration
    def test_budget_rollover_with_overspending(self, app, client, auth_headers, sample_budgets, sample_categories):
        """Test that overspending carries forward as deficit."""
        # Create a MonthlyBudgetSnapshot for January with overspending
        with app.app_context():
            snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01',
                monthly_amount=100,
                carried_surplus=0,
                carried_deficit=0,
                actual_spent=150.00  # Spent 150, so 50 deficit
            )
            db.session.add(snapshot)
            db.session.commit()

        # Move to February and check budget
        with freeze_time("2025-02-15"):
            response = client.get('/api/budgets', headers=auth_headers())
            data = response.get_json()
            budgets = data['categories']
            beauty_budget = next(b for b in budgets if b['category'] == 'Beauty')

            # Deficit should be carried forward and shown as spending
            # API doesn't return carried_deficit, but current_spent reflects it
            assert beauty_budget['effective_budget'] == 100.00  # Budget stays at monthly amount
            assert beauty_budget['current_spent'] == 50.00  # Deficit shown as spending
            assert beauty_budget['remaining'] == 50.00  # 100 - 50

    @pytest.mark.integration
    def test_budget_rollover_multiple_months(self, app, client, auth_headers, sample_budgets, sample_categories):
        """Test budget rollover across multiple months."""
        # Create snapshots for January and February
        with app.app_context():
            # January: Spend 70 (30 surplus)
            jan_snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01',
                monthly_amount=100,
                carried_surplus=0,
                carried_deficit=0,
                actual_spent=70.00
            )
            # February: Spend 80 with 30 carried surplus (20 net surplus: 30 + 100 - 80)
            feb_snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-02',
                monthly_amount=100,
                carried_surplus=30,
                carried_deficit=0,
                actual_spent=80.00
            )
            db.session.add_all([jan_snapshot, feb_snapshot])
            db.session.commit()

        # March: Check cumulative balance
        with freeze_time("2025-03-15"):
            response = client.get('/api/budgets', headers=auth_headers())
            data = response.get_json()
            budgets = data['categories']
            beauty_budget = next(b for b in budgets if b['category'] == 'Beauty')

            # Jan: 100 - 70 = +30
            # Feb: 30 + 100 - 80 = +50
            # API doesn't return carried_surplus, but effective_budget reflects it
            assert beauty_budget['effective_budget'] == 150.00  # 100 + 50 surplus
            assert beauty_budget['current_spent'] == 0  # No spending in March yet
            assert beauty_budget['remaining'] == 150.00


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

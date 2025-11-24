"""
Tests for expense deletion functionality.

These tests verify that:
- Users can delete their own expenses
- Users cannot delete other users' expenses
- Deleting expenses recalculates snapshots for past months
- Deletion returns appropriate error codes
"""
import pytest
from datetime import datetime
from freezegun import freeze_time
from models import db, Expense, Budget, Category, MonthlyBudgetSnapshot


class TestExpenseDelete:
    """Test expense deletion endpoint."""

    @pytest.mark.unit
    def test_delete_own_expense(self, app, client, auth_headers, sample_categories):
        """Test that a user can delete their own expense."""
        # Create budget and expense
        with app.app_context():
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)
            db.session.commit()

        # Create expense
        response = client.post(
            '/api/expenses',
            json={
                'amount': 50.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-15'
            },
            headers=auth_headers()
        )
        assert response.status_code == 201
        expense_id = response.get_json()['id']

        # Delete expense
        response = client.delete(
            f'/api/expenses/{expense_id}',
            headers=auth_headers()
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        assert 'deleted successfully' in data['message'].lower()

        # Verify expense is deleted
        response = client.get('/api/expenses', headers=auth_headers())
        expenses = response.get_json()
        assert not any(exp['id'] == expense_id for exp in expenses)

    @pytest.mark.unit
    def test_delete_nonexistent_expense(self, client, auth_headers):
        """Test deleting an expense that doesn't exist."""
        response = client.delete(
            '/api/expenses/99999',
            headers=auth_headers()
        )
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'not found' in data['error'].lower()

    @pytest.mark.unit
    def test_delete_other_user_expense(self, app, client, auth_headers, auth_headers_user2, sample_categories):
        """Test that a user cannot delete another user's expense."""
        # Create budget and expense for user1
        with app.app_context():
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)
            db.session.commit()

        # Create expense as user1
        response = client.post(
            '/api/expenses',
            json={
                'amount': 50.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-15'
            },
            headers=auth_headers()
        )
        assert response.status_code == 201
        expense_id = response.get_json()['id']

        # Try to delete as user2
        response = client.delete(
            f'/api/expenses/{expense_id}',
            headers=auth_headers_user2()
        )
        assert response.status_code == 403
        data = response.get_json()
        assert 'error' in data
        assert 'permission' in data['error'].lower()

        # Verify expense still exists
        response = client.get('/api/expenses', headers=auth_headers())
        expenses = response.get_json()
        assert any(exp['id'] == expense_id for exp in expenses)

    @pytest.mark.unit
    def test_delete_shared_expense_permission(self, app, client, auth_headers, auth_headers_user2, sample_categories):
        """Test that users can only delete their own shared expenses."""
        # Create shared budget
        with app.app_context():
            budget = Budget(
                category_id=sample_categories['Groceries'],
                user=None,  # Shared category
                monthly_amount=1000
            )
            db.session.add(budget)
            db.session.commit()

        # Create expense as user1
        response = client.post(
            '/api/expenses',
            json={
                'amount': 50.00,
                'category_id': sample_categories['Groceries'],
                'expense_date': '2025-01-15'
            },
            headers=auth_headers()
        )
        assert response.status_code == 201
        expense_id = response.get_json()['id']

        # User2 should not be able to delete user1's expense
        response = client.delete(
            f'/api/expenses/{expense_id}',
            headers=auth_headers_user2()
        )
        assert response.status_code == 403

        # User1 should be able to delete their own expense
        response = client.delete(
            f'/api/expenses/{expense_id}',
            headers=auth_headers()
        )
        assert response.status_code == 200

    @pytest.mark.integration
    @freeze_time("2025-03-15")
    def test_delete_past_month_expense_recalculates_snapshots(self, app, client, auth_headers, sample_categories):
        """Test that deleting a past month expense recalculates snapshots."""
        from datetime import date

        with app.app_context():
            # Create budget
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)

            # Create expense in January
            expense = Expense(
                amount=50.00,
                category_id=sample_categories['Beauty'],
                created_by='user1',
                expense_date=date(2025, 1, 15)
            )
            db.session.add(expense)

            # Create snapshot for January (as if month has been finalized)
            snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01',
                monthly_amount=100,
                carried_surplus=0,
                carried_deficit=0,
                actual_spent=50.00
            )
            db.session.add(snapshot)
            db.session.commit()

            expense_id = expense.id

            # Verify snapshot exists with correct spending
            snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01'
            ).first()
            assert snapshot is not None
            assert snapshot.actual_spent == 50.00

        # Delete expense in March (current time)
        response = client.delete(
            f'/api/expenses/{expense_id}',
            headers=auth_headers()
        )
        assert response.status_code == 200

        # Verify January snapshot was recalculated to reflect zero spending
        with app.app_context():
            snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01'
            ).first()
            assert snapshot is not None
            assert snapshot.actual_spent == 0.00

    @pytest.mark.integration
    @freeze_time("2025-02-15")
    def test_delete_current_month_expense_no_snapshot_recalc(self, app, client, auth_headers, sample_categories):
        """Test that deleting a current month expense doesn't trigger snapshot recalculation."""
        # Create budget
        with app.app_context():
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)
            db.session.commit()

        # Create expense in current month
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
        expense_id = response.get_json()['id']

        # Verify no snapshot exists for current month
        with app.app_context():
            snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-02'
            ).first()
            assert snapshot is None

        # Delete expense
        response = client.delete(
            f'/api/expenses/{expense_id}',
            headers=auth_headers()
        )
        assert response.status_code == 200

        # Verify expense is deleted and budget reflects the change
        response = client.get('/api/budgets?month=2025-02', headers=auth_headers())
        assert response.status_code == 200
        budgets = response.get_json()['categories']
        beauty_budget = next(b for b in budgets if b['category_id'] == sample_categories['Beauty'])
        assert beauty_budget['current_spent'] == 0.00

    @pytest.mark.unit
    @freeze_time("2025-01-20")
    def test_delete_expense_updates_budget_display(self, app, client, auth_headers, sample_categories):
        """Test that deleting an expense updates the budget display correctly."""
        # Create budget
        with app.app_context():
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)
            db.session.commit()

        # Create two expenses
        client.post(
            '/api/expenses',
            json={
                'amount': 30.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-15'
            },
            headers=auth_headers()
        )

        response = client.post(
            '/api/expenses',
            json={
                'amount': 20.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-16'
            },
            headers=auth_headers()
        )
        expense_id = response.get_json()['id']

        # Check budget shows total spent
        response = client.get('/api/budgets', headers=auth_headers())
        budgets = response.get_json()['categories']
        beauty_budget = next(b for b in budgets if b['category_id'] == sample_categories['Beauty'])
        assert beauty_budget['current_spent'] == 50.00
        assert beauty_budget['remaining'] == 50.00

        # Delete one expense
        client.delete(f'/api/expenses/{expense_id}', headers=auth_headers())

        # Check budget updated
        response = client.get('/api/budgets', headers=auth_headers())
        budgets = response.get_json()['categories']
        beauty_budget = next(b for b in budgets if b['category_id'] == sample_categories['Beauty'])
        assert beauty_budget['current_spent'] == 30.00
        assert beauty_budget['remaining'] == 70.00

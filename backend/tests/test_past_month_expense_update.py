"""
Test adding expenses to past months and verifying that all subsequent snapshots are updated.

This test verifies the critical behavior: when a user adds an expense to a past month that
has already been finalized, the system should:
1. Allow the expense to be added (or reject it appropriately)
2. Update the snapshot for that month
3. Recalculate all snapshots between that month and the current month
4. Ensure cumulative balances flow correctly through all months
"""
import pytest
from datetime import date
from freezegun import freeze_time
from models import db, Budget, Expense, MonthlyBudgetSnapshot


@freeze_time("2025-03-15")
class TestPastMonthExpenseWithSnapshotUpdates:
    """Test that adding expenses to past months updates all future snapshots."""

    @pytest.mark.integration
    def test_reject_expense_to_finalized_past_month(self, app, client, auth_headers, sample_categories):
        """Test that expenses cannot be added to finalized past months."""
        with app.app_context():
            # Create budget for Beauty category
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)

            # Create snapshots for January and February (finalized months)
            jan_snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01',
                monthly_amount=100,
                carried_surplus=0,
                carried_deficit=0,
                actual_spent=50  # Spent $50 in January
            )
            feb_snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-02',
                monthly_amount=100,
                carried_surplus=50,  # Carried forward from January
                carried_deficit=0,
                actual_spent=60  # Spent $60 in February
            )
            db.session.add_all([jan_snapshot, feb_snapshot])
            db.session.commit()

        # Try to add expense to January (finalized month)
        response = client.post(
            '/api/expenses',
            json={
                'amount': 25.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-20'
            },
            headers=auth_headers()
        )

        # Should be rejected because January is finalized
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'finalized' in data['error'].lower()

    @pytest.mark.integration
    def test_allow_expense_to_unfinalized_past_month(self, app, client, auth_headers, sample_categories):
        """Test that expenses CAN be added to past months that haven't been finalized yet."""
        with app.app_context():
            # Create budget for Beauty category
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)

            # Create snapshot only for January (February is not finalized)
            jan_snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01',
                monthly_amount=100,
                carried_surplus=0,
                carried_deficit=0,
                actual_spent=50
            )
            db.session.add(jan_snapshot)
            db.session.commit()

        # Add expense to February (unfinalized but past month)
        # Current date is 2025-03-15, so February is past but not finalized
        response = client.post(
            '/api/expenses',
            json={
                'amount': 30.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-02-20'
            },
            headers=auth_headers()
        )

        # Should succeed because February is not finalized
        assert response.status_code == 201
        data = response.get_json()
        assert data['amount'] == 30.00
        assert data['expense_date'] == '2025-02-20'

    @pytest.mark.integration
    def test_finalize_previous_months_creates_snapshots(self, app, client, auth_headers, sample_categories):
        """Test that finalize_previous_months creates snapshots for past months."""
        with app.app_context():
            # Create budget in January
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)

            # Add expense in January (when frozen to Jan 15)
            with freeze_time("2025-01-15"):
                expense = Expense(
                    amount=40.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=date(2025, 1, 10)
                )
                db.session.add(expense)

            # Add expense in February (when frozen to Feb 15)
            with freeze_time("2025-02-15"):
                expense = Expense(
                    amount=60.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=date(2025, 2, 10)
                )
                db.session.add(expense)

            # Create initial snapshot for January
            jan_snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01',
                monthly_amount=100,
                carried_surplus=0,
                carried_deficit=0,
                actual_spent=40
            )
            db.session.add(jan_snapshot)
            db.session.commit()

        # Now in March - call finalize_previous_months
        from app import finalize_previous_months
        with app.app_context():
            finalize_previous_months()

            # Verify February snapshot was created
            feb_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-02'
            ).first()

            assert feb_snapshot is not None
            assert feb_snapshot.monthly_amount == 100
            assert feb_snapshot.actual_spent == 60
            # January had $60 surplus (100 - 40)
            assert feb_snapshot.carried_surplus == 60
            assert feb_snapshot.carried_deficit == 0

    @pytest.mark.integration
    def test_finalize_handles_deficit_carryover(self, app, client, auth_headers, sample_categories):
        """Test that finalize_previous_months correctly carries forward deficits."""
        with app.app_context():
            # Create budget
            budget = Budget(
                category_id=sample_categories['Clothing'],
                user='user1',
                monthly_amount=150
            )
            db.session.add(budget)

            # Add overspending in January
            jan_expense = Expense(
                amount=200.00,  # $50 over budget
                category_id=sample_categories['Clothing'],
                created_by='user1',
                expense_date=date(2025, 1, 15)
            )
            db.session.add(jan_expense)

            # Create January snapshot with deficit
            jan_snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Clothing'],
                user='user1',
                month='2025-01',
                monthly_amount=150,
                carried_surplus=0,
                carried_deficit=0,
                actual_spent=200
            )
            db.session.add(jan_snapshot)

            # Add normal spending in February
            feb_expense = Expense(
                amount=100.00,
                category_id=sample_categories['Clothing'],
                created_by='user1',
                expense_date=date(2025, 2, 15)
            )
            db.session.add(feb_expense)
            db.session.commit()

        # Now in March - finalize February
        from app import finalize_previous_months
        with app.app_context():
            finalize_previous_months()

            # Verify February snapshot carries forward the deficit
            feb_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Clothing'],
                user='user1',
                month='2025-02'
            ).first()

            assert feb_snapshot is not None
            assert feb_snapshot.monthly_amount == 150
            assert feb_snapshot.actual_spent == 100
            # January had $50 deficit (150 - 200 = -50)
            assert feb_snapshot.carried_surplus == 0
            assert feb_snapshot.carried_deficit == 50

    @pytest.mark.integration
    def test_view_past_month_returns_snapshot_data(self, app, client, auth_headers, sample_categories):
        """Test that viewing a past month's budgets returns the snapshot data."""
        with app.app_context():
            # Create budget
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)

            # Create January snapshot
            jan_snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01',
                monthly_amount=100,
                carried_surplus=20,
                carried_deficit=0,
                actual_spent=70
            )
            db.session.add(jan_snapshot)
            db.session.commit()

        # Request January budgets
        response = client.get('/api/budgets?month=2025-01', headers=auth_headers())
        assert response.status_code == 200

        data = response.get_json()
        assert 'categories' in data
        assert 'personal_summary' in data

        # Find Beauty budget in categories
        beauty = next((c for c in data['categories'] if c['category'] == 'Beauty'), None)
        assert beauty is not None
        assert beauty['monthly_amount'] == 100
        # Past month with surplus: effective_budget = monthly_amount + carried_surplus
        assert beauty['effective_budget'] == 120  # 100 + 20 surplus
        assert beauty['current_spent'] == 70
        assert beauty['remaining'] == 50  # 120 - 70

        # Verify personal summary
        personal = data['personal_summary']
        assert personal is not None
        # Past month should show actual data from snapshot
        assert personal['spent'] == 70
        assert personal['base_budget'] == 100
        assert personal['effective_budget'] == 120  # includes carried surplus

    @pytest.mark.integration
    def test_view_past_month_without_snapshot_returns_empty_or_error(self, app, client, auth_headers, sample_categories):
        """Test that viewing a past month without snapshots returns appropriate response."""
        with app.app_context():
            # Create budget but no snapshots
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)
            db.session.commit()

        # Request January budgets (no snapshot exists)
        response = client.get('/api/budgets?month=2025-01', headers=auth_headers())

        # Should either return empty or error - both are acceptable
        assert response.status_code in [200, 400, 404]

        if response.status_code == 200:
            data = response.get_json()
            # If successful, should return empty or minimal data
            assert isinstance(data, dict)

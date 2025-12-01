"""
End-to-end tests for monthly rollover behavior.

These tests simulate real-world scenarios where users have expenses in one month,
then the month rolls over, and we need to ensure snapshots are created properly.
"""
import pytest
from datetime import datetime
from freezegun import freeze_time
from dateutil.relativedelta import relativedelta
from models import db, Budget, Expense, MonthlyBudgetSnapshot, Category


def test_monthly_rollover_first_snapshot_created(client, auth_headers, sample_categories):
    """
    Test the most critical scenario: NO snapshots exist yet, and we roll over to a new month.
    This simulates the production bug where November expenses existed but no November snapshot
    was created when December started.
    """
    # Freeze time to November 15, 2025
    with freeze_time("2025-11-15"):
        with client.application.app_context():
            # Create budgets (this is like having budgets set up)
            beauty_budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            groceries_budget = Budget(
                category_id=sample_categories['Groceries'],
                user=None,  # Shared
                monthly_amount=1200
            )
            db.session.add_all([beauty_budget, groceries_budget])
            db.session.commit()

            # Create expenses in November
            expenses = [
                Expense(
                    amount=30.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=datetime(2025, 11, 10).date()
                ),
                Expense(
                    amount=45.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=datetime(2025, 11, 14).date()
                ),
                Expense(
                    amount=250.00,
                    category_id=sample_categories['Groceries'],
                    created_by='user1',
                    expense_date=datetime(2025, 11, 12).date()
                ),
            ]
            db.session.add_all(expenses)
            db.session.commit()

            # Verify no snapshots exist yet
            assert MonthlyBudgetSnapshot.query.count() == 0

        # Still in November, check budgets endpoint
        response = client.get('/api/budgets', headers=auth_headers())
        assert response.status_code == 200
        data = response.get_json()

        # In November, we should see current spending
        beauty = next(b for b in data['categories'] if b['category'] == 'Beauty')
        assert beauty['current_spent'] == 75.00  # 30 + 45
        assert beauty['remaining'] == 25.00  # 100 - 75

    # NOW ROLL OVER TO DECEMBER 1st - This is where the bug occurs!
    with freeze_time("2025-12-01 10:00:00"):
        # Make a request to the budgets endpoint in December
        response = client.get('/api/budgets', headers=auth_headers())
        assert response.status_code == 200

        with client.application.app_context():
            # CRITICAL: November snapshot should now exist!
            nov_snapshots = MonthlyBudgetSnapshot.query.filter_by(month='2025-11').all()
            assert len(nov_snapshots) > 0, "November snapshots should be created when accessing budgets in December"

            # Check Beauty snapshot
            beauty_snapshot = next((s for s in nov_snapshots if s.category_id == sample_categories['Beauty']), None)
            assert beauty_snapshot is not None, "Beauty snapshot for November should exist"
            assert beauty_snapshot.actual_spent == 75.00
            assert beauty_snapshot.monthly_amount == 100
            assert beauty_snapshot.carried_surplus == 0
            assert beauty_snapshot.carried_deficit == 0

            # Check Groceries snapshot
            groceries_snapshot = next((s for s in nov_snapshots if s.category_id == sample_categories['Groceries']), None)
            assert groceries_snapshot is not None, "Groceries snapshot for November should exist"
            assert groceries_snapshot.actual_spent == 250.00
            assert groceries_snapshot.monthly_amount == 1200

        # Check that December budgets show the carried balance from November
        data = response.get_json()
        beauty = next(b for b in data['categories'] if b['category'] == 'Beauty')

        # November ended with $25 surplus (100 budget - 75 spent)
        # December should start with that surplus added to budget
        assert beauty['effective_budget'] == 125.00  # 100 + 25 surplus
        assert beauty['current_spent'] == 0  # No December spending yet
        assert beauty['remaining'] == 125.00


def test_monthly_rollover_with_existing_snapshots(client, auth_headers, sample_categories):
    """
    Test rollover when snapshots already exist from previous months.
    This ensures the fix doesn't break the existing functionality.
    """
    # Start in October with an existing snapshot
    with freeze_time("2025-10-01"):
        with client.application.app_context():
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)
            db.session.commit()

    # Move to October 20, add expenses
    with freeze_time("2025-10-20"):
        with client.application.app_context():
            expense = Expense(
                amount=60.00,
                category_id=sample_categories['Beauty'],
                created_by='user1',
                expense_date=datetime(2025, 10, 20).date()
            )
            db.session.add(expense)
            db.session.commit()

    # Move to November 1 - this should finalize October
    with freeze_time("2025-11-01 10:00:00"):
        response = client.get('/api/budgets', headers=auth_headers())
        assert response.status_code == 200

        with client.application.app_context():
            # October snapshot should exist
            oct_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                month='2025-10',
                category_id=sample_categories['Beauty']
            ).first()
            assert oct_snapshot is not None
            assert oct_snapshot.actual_spent == 60.00

        # November should show carried surplus
        data = response.get_json()
        beauty = next(b for b in data['categories'] if b['category'] == 'Beauty')
        assert beauty['effective_budget'] == 140.00  # 100 + 40 surplus

    # Add November expenses
    with freeze_time("2025-11-15"):
        with client.application.app_context():
            expense = Expense(
                amount=120.00,  # Over budget
                category_id=sample_categories['Beauty'],
                created_by='user1',
                expense_date=datetime(2025, 11, 15).date()
            )
            db.session.add(expense)
            db.session.commit()

    # Move to December - should finalize November with deficit
    with freeze_time("2025-12-01 10:00:00"):
        response = client.get('/api/budgets', headers=auth_headers())
        assert response.status_code == 200

        with client.application.app_context():
            # November snapshot should exist
            nov_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                month='2025-11',
                category_id=sample_categories['Beauty']
            ).first()
            assert nov_snapshot is not None
            assert nov_snapshot.actual_spent == 120.00
            assert nov_snapshot.carried_surplus == 40.00  # From October
            # Net balance: 40 + 100 - 120 = 20 surplus
            # So December should carry 20 surplus

        # December should show small surplus from November
        data = response.get_json()
        beauty = next(b for b in data['categories'] if b['category'] == 'Beauty')
        # Ending balance from Nov: 40 (carried) + 100 (budget) - 120 (spent) = 20 surplus
        assert beauty['effective_budget'] == 120.00  # 100 + 20 surplus


def test_monthly_rollover_skips_months_without_activity(client, auth_headers, sample_categories):
    """
    Test that if multiple months pass with no API access, all snapshots are created.
    This tests the while loop in finalize_previous_months().
    """
    # Start in October
    with freeze_time("2025-10-15"):
        with client.application.app_context():
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            expense = Expense(
                amount=50.00,
                category_id=sample_categories['Beauty'],
                created_by='user1',
                expense_date=datetime(2025, 10, 15).date()
            )
            db.session.add_all([budget, expense])
            db.session.commit()

    # Move to November 1 - finalize October
    with freeze_time("2025-11-01"):
        response = client.get('/api/budgets', headers=auth_headers())
        assert response.status_code == 200

    # Jump directly to January (skipping December access)
    # This simulates no one checking budgets in December
    with freeze_time("2026-01-05"):
        response = client.get('/api/budgets', headers=auth_headers())
        assert response.status_code == 200

        with client.application.app_context():
            # Both November and December snapshots should be created
            snapshots = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty']
            ).order_by(MonthlyBudgetSnapshot.month).all()

            months = [s.month for s in snapshots]
            assert '2025-10' in months, "October snapshot should exist"
            assert '2025-11' in months, "November snapshot should exist (no expenses)"
            assert '2025-12' in months, "December snapshot should exist (no expenses)"

            # November snapshot (no expenses)
            nov_snapshot = next(s for s in snapshots if s.month == '2025-11')
            assert nov_snapshot.actual_spent == 0
            assert nov_snapshot.carried_surplus == 50.00  # From October

            # December snapshot (no expenses)
            dec_snapshot = next(s for s in snapshots if s.month == '2025-12')
            assert dec_snapshot.actual_spent == 0
            # Carried from Nov: 50 + 100 - 0 = 150
            assert dec_snapshot.carried_surplus == 150.00


def test_monthly_rollover_multiple_budgets_simultaneously(client, auth_headers, sample_categories):
    """
    Test that ALL budgets get finalized when month rolls over, not just one.
    """
    with freeze_time("2025-11-15"):
        with client.application.app_context():
            # Create multiple budgets
            budgets = [
                Budget(category_id=sample_categories['Beauty'], user='user1', monthly_amount=100),
                Budget(category_id=sample_categories['Clothing'], user='user1', monthly_amount=150),
                Budget(category_id=sample_categories['Groceries'], user=None, monthly_amount=1200),
                Budget(category_id=sample_categories['Car'], user=None, monthly_amount=300),
            ]
            db.session.add_all(budgets)

            # Add expenses to each
            expenses = [
                Expense(amount=75.00, category_id=sample_categories['Beauty'],
                       created_by='user1', expense_date=datetime(2025, 11, 10).date()),
                Expense(amount=200.00, category_id=sample_categories['Clothing'],
                       created_by='user1', expense_date=datetime(2025, 11, 12).date()),
                Expense(amount=800.00, category_id=sample_categories['Groceries'],
                       created_by='user1', expense_date=datetime(2025, 11, 14).date()),
                Expense(amount=150.00, category_id=sample_categories['Car'],
                       created_by='user2', expense_date=datetime(2025, 11, 8).date()),
            ]
            db.session.add_all(expenses)
            db.session.commit()

    # Roll over to December
    with freeze_time("2025-12-01"):
        response = client.get('/api/budgets', headers=auth_headers())
        assert response.status_code == 200

        with client.application.app_context():
            # ALL budgets should have November snapshots
            nov_snapshots = MonthlyBudgetSnapshot.query.filter_by(month='2025-11').all()
            assert len(nov_snapshots) == 4, "All 4 budgets should have November snapshots"

            # Verify each one
            snapshot_by_category = {s.category.name: s for s in nov_snapshots}

            assert 'Beauty' in snapshot_by_category
            assert snapshot_by_category['Beauty'].actual_spent == 75.00

            assert 'Clothing' in snapshot_by_category
            assert snapshot_by_category['Clothing'].actual_spent == 200.00

            assert 'Groceries' in snapshot_by_category
            assert snapshot_by_category['Groceries'].actual_spent == 800.00

            assert 'Car' in snapshot_by_category
            assert snapshot_by_category['Car'].actual_spent == 150.00


def test_monthly_rollover_at_exact_midnight(client, auth_headers, sample_categories):
    """
    Test the edge case of accessing the API right at midnight on the 1st of the month.
    """
    with freeze_time("2025-11-30 23:59:59"):
        with client.application.app_context():
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            expense = Expense(
                amount=60.00,
                category_id=sample_categories['Beauty'],
                created_by='user1',
                expense_date=datetime(2025, 11, 30).date()
            )
            db.session.add_all([budget, expense])
            db.session.commit()

    # Access at exactly midnight
    with freeze_time("2025-12-01 00:00:00"):
        response = client.get('/api/budgets', headers=auth_headers())
        assert response.status_code == 200

        with client.application.app_context():
            # November snapshot should be created
            snapshot = MonthlyBudgetSnapshot.query.filter_by(
                month='2025-11',
                category_id=sample_categories['Beauty']
            ).first()
            assert snapshot is not None
            assert snapshot.actual_spent == 60.00

"""
Test that adding expenses to past months triggers snapshot recalculation.

When a user adds an expense to a past month that already has a finalized snapshot,
the system should:
1. Allow the expense to be added
2. Delete the snapshot for that month
3. Delete all subsequent snapshots (up to current month)
4. Recalculate and recreate all snapshots from that month forward
5. Ensure the cumulative balance flows correctly through all months
"""
import pytest
from datetime import date
from freezegun import freeze_time
from models import db, Budget, Expense, MonthlyBudgetSnapshot


@freeze_time("2025-04-15")
class TestPastMonthSnapshotRecalculation:
    """Test snapshot recalculation when expenses are added to past months."""

    @pytest.mark.integration
    def test_add_expense_to_finalized_month_recalculates_snapshots(self, app, client, auth_headers, sample_categories):
        """Test that adding an expense to a finalized month recalculates all future snapshots."""
        with app.app_context():
            # Create budget
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)

            # Create actual expense records that the snapshots represent
            expenses = [
                Expense(
                    amount=50.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=date(2025, 1, 10)
                ),
                Expense(
                    amount=70.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=date(2025, 2, 15)
                ),
                Expense(
                    amount=60.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=date(2025, 3, 20)
                )
            ]
            db.session.add_all(expenses)

            # Create snapshots for January, February, March (all finalized)
            snapshots = [
                MonthlyBudgetSnapshot(
                    category_id=sample_categories['Beauty'],
                    user='user1',
                    month='2025-01',
                    monthly_amount=100,
                    carried_surplus=0,
                    carried_deficit=0,
                    actual_spent=50  # Spent $50, surplus $50
                ),
                MonthlyBudgetSnapshot(
                    category_id=sample_categories['Beauty'],
                    user='user1',
                    month='2025-02',
                    monthly_amount=100,
                    carried_surplus=50,  # Carried from January
                    carried_deficit=0,
                    actual_spent=70  # Spent $70, net surplus $80
                ),
                MonthlyBudgetSnapshot(
                    category_id=sample_categories['Beauty'],
                    user='user1',
                    month='2025-03',
                    monthly_amount=100,
                    carried_surplus=80,  # Carried from February
                    carried_deficit=0,
                    actual_spent=60  # Spent $60, net surplus $120
                )
            ]
            db.session.add_all(snapshots)
            db.session.commit()

            # Verify initial state
            march_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-03'
            ).first()
            assert march_snapshot.actual_spent == 60
            assert march_snapshot.carried_surplus == 80

        # Now add an expense to January (changes the starting point)
        response = client.post(
            '/api/expenses',
            json={
                'amount': 30.00,  # Add $30 to January
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-20'
            },
            headers=auth_headers()
        )

        # Should succeed
        assert response.status_code == 201
        data = response.get_json()
        assert data['amount'] == 30.00

        # Verify snapshots were recalculated
        with app.app_context():
            # January should now show $80 spent (50 + 30)
            jan_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01'
            ).first()
            assert jan_snapshot.actual_spent == 80  # 50 + 30
            # Surplus reduced from $50 to $20

            # February should have recalculated carried surplus
            feb_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-02'
            ).first()
            assert feb_snapshot.carried_surplus == 20  # January surplus reduced
            assert feb_snapshot.actual_spent == 70  # Unchanged
            # Net balance: 20 + 100 - 70 = 50

            # March should have recalculated carried surplus
            march_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-03'
            ).first()
            assert march_snapshot.carried_surplus == 50  # February net balance
            assert march_snapshot.actual_spent == 60  # Unchanged
            # Net balance: 50 + 100 - 60 = 90

    @pytest.mark.integration
    def test_add_expense_to_middle_month_recalculates_forward(self, app, client, auth_headers, sample_categories):
        """Test that adding expense to a middle month only recalculates from that month forward."""
        with app.app_context():
            # Create budget
            budget = Budget(
                category_id=sample_categories['Clothing'],
                user='user1',
                monthly_amount=150
            )
            db.session.add(budget)

            # Create actual expense records that the snapshots represent
            expenses = [
                Expense(
                    amount=100.00,
                    category_id=sample_categories['Clothing'],
                    created_by='user1',
                    expense_date=date(2025, 1, 15)
                ),
                Expense(
                    amount=120.00,
                    category_id=sample_categories['Clothing'],
                    created_by='user1',
                    expense_date=date(2025, 2, 20)
                ),
                Expense(
                    amount=90.00,
                    category_id=sample_categories['Clothing'],
                    created_by='user1',
                    expense_date=date(2025, 3, 10)
                )
            ]
            db.session.add_all(expenses)

            # Create snapshots for Jan, Feb, Mar
            snapshots = [
                MonthlyBudgetSnapshot(
                    category_id=sample_categories['Clothing'],
                    user='user1',
                    month='2025-01',
                    monthly_amount=150,
                    carried_surplus=0,
                    carried_deficit=0,
                    actual_spent=100  # Surplus $50
                ),
                MonthlyBudgetSnapshot(
                    category_id=sample_categories['Clothing'],
                    user='user1',
                    month='2025-02',
                    monthly_amount=150,
                    carried_surplus=50,
                    carried_deficit=0,
                    actual_spent=120  # Net surplus $80
                ),
                MonthlyBudgetSnapshot(
                    category_id=sample_categories['Clothing'],
                    user='user1',
                    month='2025-03',
                    monthly_amount=150,
                    carried_surplus=80,
                    carried_deficit=0,
                    actual_spent=90  # Net surplus $140
                )
            ]
            db.session.add_all(snapshots)
            db.session.commit()

        # Add expense to February
        response = client.post(
            '/api/expenses',
            json={
                'amount': 50.00,  # Add $50 to February
                'category_id': sample_categories['Clothing'],
                'expense_date': '2025-02-10'
            },
            headers=auth_headers()
        )

        assert response.status_code == 201

        with app.app_context():
            # January should be unchanged
            jan_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Clothing'],
                user='user1',
                month='2025-01'
            ).first()
            assert jan_snapshot.actual_spent == 100
            assert jan_snapshot.carried_surplus == 0

            # February should be recalculated
            feb_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Clothing'],
                user='user1',
                month='2025-02'
            ).first()
            assert feb_snapshot.actual_spent == 170  # 120 + 50
            assert feb_snapshot.carried_surplus == 50  # From January
            # Net balance: 50 + 150 - 170 = 30

            # March should be recalculated with new February balance
            march_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Clothing'],
                user='user1',
                month='2025-03'
            ).first()
            assert march_snapshot.carried_surplus == 30  # New February net
            assert march_snapshot.actual_spent == 90  # Unchanged
            # Net balance: 30 + 150 - 90 = 90

    @pytest.mark.integration
    def test_add_expense_creating_deficit_recalculates_correctly(self, app, client, auth_headers, sample_categories):
        """Test that adding an expense that creates a deficit recalculates correctly."""
        with app.app_context():
            # Create budget
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)

            # Create actual expense records that the snapshots represent
            expenses = [
                Expense(
                    amount=60.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=date(2025, 1, 15)
                ),
                Expense(
                    amount=50.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=date(2025, 2, 20)
                )
            ]
            db.session.add_all(expenses)

            # Create snapshots with surplus
            snapshots = [
                MonthlyBudgetSnapshot(
                    category_id=sample_categories['Beauty'],
                    user='user1',
                    month='2025-01',
                    monthly_amount=100,
                    carried_surplus=0,
                    carried_deficit=0,
                    actual_spent=60  # Surplus $40
                ),
                MonthlyBudgetSnapshot(
                    category_id=sample_categories['Beauty'],
                    user='user1',
                    month='2025-02',
                    monthly_amount=100,
                    carried_surplus=40,
                    carried_deficit=0,
                    actual_spent=50  # Net surplus $90
                )
            ]
            db.session.add_all(snapshots)
            db.session.commit()

        # Add large expense to January that creates deficit
        response = client.post(
            '/api/expenses',
            json={
                'amount': 80.00,  # Total Jan spending: 60 + 80 = 140 (deficit $40)
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-25'
            },
            headers=auth_headers()
        )

        assert response.status_code == 201

        with app.app_context():
            # January should now have deficit
            jan_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01'
            ).first()
            assert jan_snapshot.actual_spent == 140  # 60 + 80
            assert jan_snapshot.carried_surplus == 0
            assert jan_snapshot.carried_deficit == 0
            # Net balance: 100 - 140 = -40 (deficit)

            # February should carry forward deficit
            feb_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-02'
            ).first()
            assert feb_snapshot.carried_surplus == 0
            assert feb_snapshot.carried_deficit == 40  # Deficit from January
            assert feb_snapshot.actual_spent == 50
            # Net balance: -40 + 100 - 50 = 10 (surplus)

    @pytest.mark.integration
    def test_multiple_expenses_to_same_past_month(self, app, client, auth_headers, sample_categories):
        """Test adding multiple expenses to the same past month triggers recalc each time."""
        with app.app_context():
            # Create budget
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)

            # Create initial expense record that the snapshot represents
            initial_expense = Expense(
                amount=50.00,
                category_id=sample_categories['Beauty'],
                created_by='user1',
                expense_date=date(2025, 1, 5)
            )
            db.session.add(initial_expense)

            # Create January snapshot
            snapshot = MonthlyBudgetSnapshot(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01',
                monthly_amount=100,
                carried_surplus=0,
                carried_deficit=0,
                actual_spent=50
            )
            db.session.add(snapshot)
            db.session.commit()

        # Add first expense
        client.post(
            '/api/expenses',
            json={
                'amount': 10.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-10'
            },
            headers=auth_headers()
        )

        # Add second expense
        client.post(
            '/api/expenses',
            json={
                'amount': 15.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-01-20'
            },
            headers=auth_headers()
        )

        with app.app_context():
            # Snapshot should reflect both expenses
            jan_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01'
            ).first()
            assert jan_snapshot.actual_spent == 75  # 50 + 10 + 15

    @pytest.mark.integration
    def test_current_month_expenses_not_affected(self, app, client, auth_headers, sample_categories):
        """Test that adding expenses to current month doesn't trigger recalculation."""
        with app.app_context():
            # Create budget
            budget = Budget(
                category_id=sample_categories['Beauty'],
                user='user1',
                monthly_amount=100
            )
            db.session.add(budget)

            # Create actual expense records that the snapshots represent
            expenses = [
                Expense(
                    amount=50.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=date(2025, 1, 10)
                ),
                Expense(
                    amount=60.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=date(2025, 2, 15)
                ),
                Expense(
                    amount=40.00,
                    category_id=sample_categories['Beauty'],
                    created_by='user1',
                    expense_date=date(2025, 3, 20)
                )
            ]
            db.session.add_all(expenses)

            # Create snapshots for past months only
            snapshots = [
                MonthlyBudgetSnapshot(
                    category_id=sample_categories['Beauty'],
                    user='user1',
                    month='2025-01',
                    monthly_amount=100,
                    carried_surplus=0,
                    carried_deficit=0,
                    actual_spent=50
                ),
                MonthlyBudgetSnapshot(
                    category_id=sample_categories['Beauty'],
                    user='user1',
                    month='2025-02',
                    monthly_amount=100,
                    carried_surplus=50,
                    carried_deficit=0,
                    actual_spent=60
                ),
                MonthlyBudgetSnapshot(
                    category_id=sample_categories['Beauty'],
                    user='user1',
                    month='2025-03',
                    monthly_amount=100,
                    carried_surplus=90,
                    carried_deficit=0,
                    actual_spent=40
                )
            ]
            db.session.add_all(snapshots)
            db.session.commit()

            # Count initial snapshots
            initial_count = MonthlyBudgetSnapshot.query.count()

        # Add expense to current month (April)
        response = client.post(
            '/api/expenses',
            json={
                'amount': 25.00,
                'category_id': sample_categories['Beauty'],
                'expense_date': '2025-04-10'
            },
            headers=auth_headers()
        )

        assert response.status_code == 201

        with app.app_context():
            # Should not create or modify any snapshots for current month
            final_count = MonthlyBudgetSnapshot.query.count()
            assert final_count == initial_count

            # Past snapshots should be unchanged
            jan_snapshot = MonthlyBudgetSnapshot.query.filter_by(
                category_id=sample_categories['Beauty'],
                user='user1',
                month='2025-01'
            ).first()
            assert jan_snapshot.actual_spent == 50

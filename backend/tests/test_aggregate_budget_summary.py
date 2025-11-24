"""
Test aggregate budget summary calculations with asymmetric surplus/deficit rules.
"""
import pytest
from datetime import date
from freezegun import freeze_time
from models import db, Budget, Expense


@freeze_time("2025-11-24")
def test_future_month_aggregate_with_mixed_surplus_deficit(app, client, auth_headers, sample_categories, sample_budgets):
    """
    Test that future month aggregates correctly apply asymmetric rules at the aggregate level.

    Scenario using existing fixtures:
    - Beauty: $100 budget, no spending = +$100 surplus
    - Clothing: $150 budget, add $1000 expense = -$850 deficit
    - Net: $250 budget, $1000 spent = -$750 net deficit

    December should show: $250 base budget, $750 displayed as spent (deficit)
    """
    with app.app_context():
        # Add $1000 expense to Clothing in November
        expense = Expense(
            amount=1000.00,
            category_id=sample_categories['Clothing'],
            created_by='user1',
            expense_date=date(2025, 11, 15),
            description='Large clothing purchase'
        )
        db.session.add(expense)
        db.session.commit()

    # Fetch December budgets
    response = client.get('/api/budgets?month=2025-12', headers=auth_headers())
    assert response.status_code == 200

    data = response.json
    assert 'categories' in data
    assert 'personal_summary' in data
    assert 'shared_summary' in data

    # Check Personal aggregate summary
    personal = data['personal_summary']
    assert personal is not None

    # Debug: print what we're actually getting
    categories = data['categories']
    personal_cats = [c for c in categories if c['user'] == 'user1']
    print(f"\nPersonal categories: {len(personal_cats)}")
    for cat in personal_cats:
        print(f"  {cat['category']}: monthly=${cat['monthly_amount']}, remaining=${cat['remaining']}")
    print(f"Personal summary: {personal}")

    # Total base: $100 (Beauty) + $150 (Clothing) = $250
    # Total spent in Nov: $1000
    # Net balance with rollover: Beauty has +100 surplus, Clothing has -850 deficit
    # Net: +100 - 850 = -750, but aggregate remaining is: (100+100) + (150-850) = -500
    assert personal['base_budget'] == 250
    assert personal['remaining'] == -500  # Beauty +200 remaining, Clothing -700 remaining
    assert personal['effective_budget'] == 250  # Deficit doesn't increase budget (at aggregate)
    assert personal['spent'] == 750  # Deficit shown as spending

    # Clothing should show deficit as spending
    clothing = next(c for c in personal_cats if c['category_id'] == sample_categories['Clothing'])
    assert clothing['monthly_amount'] == 150
    assert clothing['effective_budget'] == 150  # Deficit doesn't increase budget
    assert clothing['current_spent'] == 850  # Deficit shown as spending
    assert clothing['remaining'] == -700  # 150 - 850

    # Beauty should show surplus in budget
    beauty = next(c for c in personal_cats if c['category_id'] == sample_categories['Beauty'])
    assert beauty['monthly_amount'] == 100
    assert beauty['effective_budget'] == 200  # 100 base + 100 surplus
    assert beauty['current_spent'] == 0
    assert beauty['remaining'] == 200


@freeze_time("2025-11-24")
def test_future_month_aggregate_with_net_surplus(app, client, auth_headers, sample_categories, sample_budgets):
    """
    Test that future month aggregates show surplus correctly at aggregate level.

    Scenario:
    - Beauty: $100 budget, $50 spent = +$50 surplus
    - Clothing: $150 budget, $50 spent = +$100 surplus
    - Net: $250 budget, $100 spent = +$150 net surplus

    December should show: $400 effective budget ($250 + $150), $0 spending
    """
    with app.app_context():
        # Add smaller expenses to both categories
        expenses = [
            Expense(
                amount=50.00,
                category_id=sample_categories['Beauty'],
                created_by='user1',
                expense_date=date(2025, 11, 10),
                description='Beauty purchase'
            ),
            Expense(
                amount=50.00,
                category_id=sample_categories['Clothing'],
                created_by='user1',
                expense_date=date(2025, 11, 15),
                description='Clothing purchase'
            )
        ]
        db.session.add_all(expenses)
        db.session.commit()

    # Fetch December budgets
    response = client.get('/api/budgets?month=2025-12', headers=auth_headers())
    assert response.status_code == 200

    data = response.json
    personal = data['personal_summary']
    assert personal is not None

    # Total base: $100 + $150 = $250
    # Total spent: $100
    # Net surplus: +$150
    assert personal['base_budget'] == 250
    assert personal['remaining'] == 400  # Same as effective_budget for future with surplus
    assert personal['effective_budget'] == 400  # $250 + $150
    assert personal['spent'] == 0  # No spending shown for surplus in future month

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_migrate import Migrate
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
import os
from dotenv import load_dotenv
from models import db, Expense, Category, Budget, MonthlyBudgetSnapshot

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"]}})
auth = HTTPBasicAuth()

# Database configuration
# DEV SERVER DATABASE: backend/data/database.db (file-based, gitignored)
# TEST DATABASE: :memory: (in-memory, configured in conftest.py)
basedir = os.path.abspath(os.path.dirname(__file__))
datadir = os.path.join(basedir, 'data')
os.makedirs(datadir, exist_ok=True)  # Ensure data directory exists
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(datadir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

# Load users from environment variables
users = {}
user1 = os.getenv('AUTH_USER1', '')
user2 = os.getenv('AUTH_USER2', '')

if user1:
    username, password_hash = user1.split(':', 1)
    users[username] = password_hash

if user2:
    username, password_hash = user2.split(':', 1)
    users[username] = password_hash

@auth.verify_password
def verify_password(username, password):
    if username in users:
        return check_password_hash(users[username], password)
    return False

# Seed categories function (call after running migrations)
def seed_categories():
    """Seed initial categories. Run with: flask seed-categories"""
    categories = [
        # Personal categories
        Category(name='Beauty', parent_type='Personal'),
        Category(name='Clothing', parent_type='Personal'),
        Category(name='Media', parent_type='Personal'),
        Category(name='Misc', parent_type='Personal'),
        Category(name='Workouts', parent_type='Personal'),
        Category(name='Dining', parent_type='Personal'),
        Category(name='Outings', parent_type='Personal'),

        # Shared categories
        Category(name='Car', parent_type='Shared'),
        Category(name='Counselling', parent_type='Shared'),
        Category(name='Groceries', parent_type='Shared'),
        Category(name='House', parent_type='Shared'),
        Category(name='Kids', parent_type='Shared'),
        Category(name='Utilities', parent_type='Shared'),
        Category(name='Entertainment', parent_type='Shared'),
    ]
    db.session.add_all(categories)
    db.session.commit()
    print(f"Seeded {len(categories)} categories")

@app.cli.command('seed-categories')
def seed_categories_command():
    """Seed the database with initial categories."""
    with app.app_context():
        if Category.query.count() == 0:
            seed_categories()
        else:
            print("Categories already exist, skipping seed")

def seed_budgets():
    """Seed initial budgets for all categories."""
    from datetime import datetime

    # TODO: Customize these budget amounts before running seed-budgets command
    # Format: (category_name, monthly_amount, user)
    # user=None for Shared categories, user='user1' or 'user2' for Personal categories

    budget_data = [
        # Shared categories (user=None)
        ('Car', 300, None),
        ('Groceries', 1200, None),
        ('House', 300, None),
        ('Kids', 750, None),
        ('Utilities', 1200, None),
        ('Counselling', 1000, None),
        ('Entertainment', 100, None),
    ]

    # add personal categories for each user in users
    for username in users.keys():
        budget_data.extend([
            ('Beauty', 100, username),
            ('Clothing', 100, username),
            ('Media', 50, username),
            ('Misc', 500, username),
            ('Workouts', 75, username),
            ('Dining', 600, username),
            ('Outings', 250, username),
        ])

    budgets = []
    for category_name, monthly_amount, user in budget_data:
        category = Category.query.filter_by(name=category_name).first()
        if category:
            budget = Budget(
                category_id=category.id,
                user=user,
                monthly_amount=monthly_amount
            )
            budgets.append(budget)

    db.session.add_all(budgets)
    db.session.commit()
    print(f"Seeded {len(budgets)} budgets")

@app.cli.command('seed-budgets')
def seed_budgets_command():
    """Seed the database with initial budgets."""
    with app.app_context():
        if Budget.query.count() == 0:
            seed_budgets()
        else:
            print("Budgets already exist, skipping seed")

@app.cli.command('show-recent')
def show_recent_command():
    """Show the 10 most recent rows from each database table."""
    with app.app_context():
        print("\n" + "="*80)
        print("EXPENSES (10 most recent)")
        print("="*80)
        expenses = Expense.query.order_by(Expense.created_at.desc()).limit(10).all()
        if expenses:
            print(f"{'ID':<5} {'Amount':<10} {'Category':<15} {'User':<10} {'Expense Date':<15} {'Created At':<20}")
            print("-"*80)
            for exp in expenses:
                print(f"{exp.id:<5} ${exp.amount:<9.2f} {exp.category.name:<15} {exp.created_by:<10} {exp.expense_date.strftime('%Y-%m-%d'):<15} {exp.created_at.strftime('%Y-%m-%d %H:%M'):<20}")
        else:
            print("No expenses found")

        print("\n" + "="*80)
        print("CATEGORIES")
        print("="*80)
        categories = Category.query.order_by(Category.id.desc()).limit(10).all()
        if categories:
            print(f"{'ID':<5} {'Name':<20} {'Parent Type':<15}")
            print("-"*80)
            for cat in categories:
                print(f"{cat.id:<5} {cat.name:<20} {cat.parent_type:<15}")
        else:
            print("No categories found")

        print("\n" + "="*80)
        print("BUDGETS")
        print("="*80)
        budgets = Budget.query.order_by(Budget.id.desc()).limit(10).all()
        if budgets:
            print(f"{'ID':<5} {'Category':<15} {'User':<10} {'Monthly Amount':<15}")
            print("-"*80)
            for budget in budgets:
                user_str = budget.user if budget.user else "(Shared)"
                print(f"{budget.id:<5} {budget.category.name:<15} {user_str:<10} ${budget.monthly_amount:<14.2f}")
        else:
            print("No budgets found")

        print("\n" + "="*80)
        print("MONTHLY BUDGET SNAPSHOTS (10 most recent months)")
        print("="*80)
        snapshots = MonthlyBudgetSnapshot.query.order_by(MonthlyBudgetSnapshot.month.desc()).limit(10).all()
        if snapshots:
            print(f"{'ID':<5} {'Month':<10} {'Category':<15} {'User':<10} {'Budget':<10} {'Spent':<10}")
            print("-"*80)
            for snap in snapshots:
                user_str = snap.user if snap.user else "(Shared)"
                print(f"{snap.id:<5} {snap.month:<10} {snap.category.name:<15} {user_str:<10} ${snap.monthly_amount:<9.2f} ${snap.actual_spent:<9.2f}")
        else:
            print("No snapshots found")

        print("\n" + "="*80)

@app.cli.command('finalize-snapshots')
def finalize_snapshots_command():
    """
    Manually trigger snapshot finalization for all past months.
    Run this after the fix to create missing November 2025 snapshots.
    """
    with app.app_context():
        from datetime import datetime
        current_month = datetime.utcnow().strftime('%Y-%m')

        print("\n" + "="*80)
        print(f"Finalizing snapshots for all past months (current month: {current_month})")
        print("="*80)

        # Count snapshots before
        before_count = MonthlyBudgetSnapshot.query.count()
        print(f"Snapshots before: {before_count}")

        # Run the finalization
        finalize_previous_months()

        # Count snapshots after
        after_count = MonthlyBudgetSnapshot.query.count()
        print(f"Snapshots after: {after_count}")
        print(f"Created {after_count - before_count} new snapshots")

        # Show what was created
        if after_count > before_count:
            print("\n" + "="*80)
            print("Newly created snapshots:")
            print("="*80)
            snapshots = MonthlyBudgetSnapshot.query.order_by(MonthlyBudgetSnapshot.month.desc()).all()
            if snapshots:
                print(f"{'Month':<10} {'Category':<15} {'User':<10} {'Budget':<10} {'Spent':<10} {'Surplus':<10} {'Deficit':<10}")
                print("-"*80)
                for snap in snapshots:
                    user_str = snap.user if snap.user else "(Shared)"
                    print(f"{snap.month:<10} {snap.category.name:<15} {user_str:<10} ${snap.monthly_amount:<9.2f} ${snap.actual_spent:<9.2f} ${snap.carried_surplus:<9.2f} ${snap.carried_deficit:<9.2f}")

        print("\n" + "="*80)
        print("Finalization complete!")
        print("="*80)

# Budget helper functions
def recalculate_snapshots_from_month(budget, start_month_str):
    """
    Recalculate all snapshots from a given month forward to current month.

    This is called when an expense is added to a past month that already has
    a snapshot. It deletes all snapshots from that month forward and recreates
    them with updated spending data.

    Args:
        budget: Budget model instance
        start_month_str: Month to start recalculation from (YYYY-MM)
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    from sqlalchemy import func

    current_month_str = datetime.utcnow().strftime('%Y-%m')

    # Don't recalculate if we're at or past current month
    if start_month_str >= current_month_str:
        return

    # Delete all snapshots from start_month forward (up to but not including current month)
    MonthlyBudgetSnapshot.query.filter(
        MonthlyBudgetSnapshot.category_id == budget.category_id,
        MonthlyBudgetSnapshot.user == budget.user,
        MonthlyBudgetSnapshot.month >= start_month_str,
        MonthlyBudgetSnapshot.month < current_month_str
    ).delete()
    db.session.commit()

    # Find the last snapshot before start_month to get the carried balance
    last_snapshot = MonthlyBudgetSnapshot.query.filter_by(
        category_id=budget.category_id,
        user=budget.user
    ).filter(
        MonthlyBudgetSnapshot.month < start_month_str
    ).order_by(MonthlyBudgetSnapshot.month.desc()).first()

    # Start recreating snapshots from start_month
    start_month_date = datetime.strptime(start_month_str, '%Y-%m')
    current_month_date = datetime.strptime(current_month_str, '%Y-%m')
    iter_month = start_month_date

    while iter_month < current_month_date:
        month_str = iter_month.strftime('%Y-%m')

        # Calculate spending for this month
        month_start = iter_month.replace(day=1).date()
        next_month = iter_month + relativedelta(months=1)
        month_end = next_month.replace(day=1).date()

        if budget.user:
            # Personal budget
            month_spent = db.session.query(func.sum(Expense.amount)).filter(
                Expense.category_id == budget.category_id,
                Expense.created_by == budget.user,
                Expense.expense_date >= month_start,
                Expense.expense_date < month_end
            ).scalar() or 0
        else:
            # Shared budget
            month_spent = db.session.query(func.sum(Expense.amount)).filter(
                Expense.category_id == budget.category_id,
                Expense.expense_date >= month_start,
                Expense.expense_date < month_end
            ).scalar() or 0

        # Calculate carried surplus/deficit
        if last_snapshot:
            last_balance = (last_snapshot.carried_surplus - last_snapshot.carried_deficit +
                           last_snapshot.monthly_amount - last_snapshot.actual_spent)
        else:
            last_balance = 0

        carried_surplus = max(0, last_balance)
        carried_deficit = max(0, -last_balance)

        # Create new snapshot
        snapshot = MonthlyBudgetSnapshot(
            category_id=budget.category_id,
            user=budget.user,
            month=month_str,
            monthly_amount=budget.monthly_amount,
            carried_surplus=carried_surplus,
            carried_deficit=carried_deficit,
            actual_spent=month_spent
        )
        db.session.add(snapshot)

        # Update last_snapshot reference for next iteration
        last_snapshot = snapshot
        iter_month = next_month

    db.session.commit()

def finalize_previous_months():
    """
    Finalize any months between the last snapshot and current system month.
    Called on first API request after month boundary.
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    from sqlalchemy import func

    current_month_str = datetime.utcnow().strftime('%Y-%m')

    # Get all budgets
    budgets = Budget.query.all()

    for budget in budgets:
        # Find the last snapshot for this budget
        last_snapshot = MonthlyBudgetSnapshot.query.filter_by(
            category_id=budget.category_id,
            user=budget.user
        ).order_by(MonthlyBudgetSnapshot.month.desc()).first()

        if last_snapshot:
            # Check if there are months to finalize between last snapshot and now
            last_month = datetime.strptime(last_snapshot.month, '%Y-%m')
            current_month = datetime.strptime(current_month_str, '%Y-%m')

            # Start from the month after the last snapshot
            iter_month = last_month + relativedelta(months=1)

            while iter_month < current_month:
                month_str = iter_month.strftime('%Y-%m')

                # Check if snapshot already exists for this month
                existing = MonthlyBudgetSnapshot.query.filter_by(
                    category_id=budget.category_id,
                    user=budget.user,
                    month=month_str
                ).first()

                if not existing:
                    # Calculate spending for this month
                    month_start = iter_month.replace(day=1).date()
                    next_month = iter_month + relativedelta(months=1)
                    month_end = next_month.replace(day=1).date()

                    if budget.user:
                        # Personal budget
                        month_spent = db.session.query(func.sum(Expense.amount)).filter(
                            Expense.category_id == budget.category_id,
                            Expense.created_by == budget.user,
                            Expense.expense_date >= month_start,
                            Expense.expense_date < month_end
                        ).scalar() or 0
                    else:
                        # Shared budget
                        month_spent = db.session.query(func.sum(Expense.amount)).filter(
                            Expense.category_id == budget.category_id,
                            Expense.expense_date >= month_start,
                            Expense.expense_date < month_end
                        ).scalar() or 0

                    # Calculate carried surplus/deficit from last snapshot
                    last_balance = (last_snapshot.carried_surplus - last_snapshot.carried_deficit +
                                    last_snapshot.monthly_amount - last_snapshot.actual_spent)

                    carried_surplus = max(0, last_balance)
                    carried_deficit = max(0, -last_balance)

                    # Create snapshot
                    snapshot = MonthlyBudgetSnapshot(
                        category_id=budget.category_id,
                        user=budget.user,
                        month=month_str,
                        monthly_amount=budget.monthly_amount,
                        carried_surplus=carried_surplus,
                        carried_deficit=carried_deficit,
                        actual_spent=month_spent
                    )
                    db.session.add(snapshot)

                    # Update last_snapshot reference for next iteration
                    last_snapshot = snapshot

                iter_month = next_month
        else:
            # No snapshots exist yet - find the earliest expense for this budget
            # and create snapshots from that month up to (but not including) current month
            current_month = datetime.strptime(current_month_str, '%Y-%m')

            if budget.user:
                # Personal budget - find earliest expense by this user in this category
                earliest_expense = Expense.query.filter_by(
                    category_id=budget.category_id,
                    created_by=budget.user
                ).order_by(Expense.expense_date).first()
            else:
                # Shared budget - find earliest expense in this category by any user
                earliest_expense = Expense.query.filter_by(
                    category_id=budget.category_id
                ).order_by(Expense.expense_date).first()

            if earliest_expense:
                # Start from the month of the earliest expense
                earliest_month = datetime(
                    earliest_expense.expense_date.year,
                    earliest_expense.expense_date.month,
                    1
                )

                # Create snapshots from earliest month up to (but not including) current month
                iter_month = earliest_month
                last_balance = 0  # Start with zero balance

                while iter_month < current_month:
                    month_str = iter_month.strftime('%Y-%m')

                    # Calculate spending for this month
                    month_start = iter_month.replace(day=1).date()
                    next_month = iter_month + relativedelta(months=1)
                    month_end = next_month.replace(day=1).date()

                    if budget.user:
                        # Personal budget
                        month_spent = db.session.query(func.sum(Expense.amount)).filter(
                            Expense.category_id == budget.category_id,
                            Expense.created_by == budget.user,
                            Expense.expense_date >= month_start,
                            Expense.expense_date < month_end
                        ).scalar() or 0
                    else:
                        # Shared budget
                        month_spent = db.session.query(func.sum(Expense.amount)).filter(
                            Expense.category_id == budget.category_id,
                            Expense.expense_date >= month_start,
                            Expense.expense_date < month_end
                        ).scalar() or 0

                    # Calculate carried surplus/deficit
                    carried_surplus = max(0, last_balance)
                    carried_deficit = max(0, -last_balance)

                    # Create snapshot
                    snapshot = MonthlyBudgetSnapshot(
                        category_id=budget.category_id,
                        user=budget.user,
                        month=month_str,
                        monthly_amount=budget.monthly_amount,
                        carried_surplus=carried_surplus,
                        carried_deficit=carried_deficit,
                        actual_spent=month_spent
                    )
                    db.session.add(snapshot)

                    # Calculate ending balance for next month
                    last_balance = last_balance + budget.monthly_amount - month_spent

                    iter_month = next_month

    db.session.commit()

def get_budget_status_for_month(budget, target_month_str, current_month_str):
    """
    Calculate budget status for a given month (past, current, or future).

    Args:
        budget: Budget model instance
        target_month_str: Month to calculate for (YYYY-MM)
        current_month_str: Current system month (YYYY-MM)

    Returns:
        Dictionary with budget status
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    from sqlalchemy import func

    target_month_date = datetime.strptime(target_month_str, '%Y-%m')
    current_month_date = datetime.strptime(current_month_str, '%Y-%m')

    is_past = target_month_str < current_month_str
    is_current = target_month_str == current_month_str
    is_future = target_month_str > current_month_str

    if is_past:
        # Past month: return snapshot if it exists
        snapshot = MonthlyBudgetSnapshot.query.filter_by(
            category_id=budget.category_id,
            user=budget.user,
            month=target_month_str
        ).first()

        if not snapshot:
            # No snapshot for this month means no budget existed then
            return None

        # Apply display rules: surplus increases budget, deficit shows as spending
        if snapshot.carried_surplus > 0:
            effective_budget = snapshot.monthly_amount + snapshot.carried_surplus
            displayed_spent = snapshot.actual_spent
        else:
            effective_budget = snapshot.monthly_amount
            displayed_spent = snapshot.actual_spent + snapshot.carried_deficit

        remaining = effective_budget - displayed_spent

        return {
            'id': budget.id,
            'category_id': budget.category_id,
            'category': budget.category.name,
            'parent_type': budget.category.parent_type,
            'user': budget.user,
            'monthly_amount': snapshot.monthly_amount,
            'effective_budget': effective_budget,
            'current_spent': displayed_spent,
            'remaining': remaining,
            'is_over_budget': remaining < 0
        }

    # For current and future months, we need to project
    # Find the last finalized snapshot
    last_snapshot = MonthlyBudgetSnapshot.query.filter_by(
        category_id=budget.category_id,
        user=budget.user
    ).order_by(MonthlyBudgetSnapshot.month.desc()).first()

    if last_snapshot:
        # Start with balance from last snapshot
        running_balance = (last_snapshot.carried_surplus - last_snapshot.carried_deficit +
                          last_snapshot.monthly_amount - last_snapshot.actual_spent)

        # Calculate through intermediate months up to (but not including) target month
        iter_month = datetime.strptime(last_snapshot.month, '%Y-%m') + relativedelta(months=1)

        while iter_month < target_month_date:
            month_str = iter_month.strftime('%Y-%m')

            # Check if this is the current month
            if month_str == current_month_str:
                # Add current month's spending
                month_start = iter_month.replace(day=1).date()
                current_date = datetime.utcnow().date()

                if budget.user:
                    month_spent = db.session.query(func.sum(Expense.amount)).filter(
                        Expense.category_id == budget.category_id,
                        Expense.created_by == budget.user,
                        Expense.expense_date >= month_start,
                        Expense.expense_date <= current_date
                    ).scalar() or 0
                else:
                    month_spent = db.session.query(func.sum(Expense.amount)).filter(
                        Expense.category_id == budget.category_id,
                        Expense.expense_date >= month_start,
                        Expense.expense_date <= current_date
                    ).scalar() or 0

                running_balance += budget.monthly_amount - month_spent
            else:
                # Future intermediate month: assume zero spending
                running_balance += budget.monthly_amount

            iter_month += relativedelta(months=1)
    else:
        # No snapshots yet - start with zero balance
        running_balance = 0

        # For future months, we need to calculate current month's balance first
        if is_future:
            # Calculate current month's spending
            month_start = current_month_date.replace(day=1).date()
            current_date = datetime.utcnow().date()

            if budget.user:
                month_spent = db.session.query(func.sum(Expense.amount)).filter(
                    Expense.category_id == budget.category_id,
                    Expense.created_by == budget.user,
                    Expense.expense_date >= month_start,
                    Expense.expense_date <= current_date
                ).scalar() or 0
            else:
                month_spent = db.session.query(func.sum(Expense.amount)).filter(
                    Expense.category_id == budget.category_id,
                    Expense.expense_date >= month_start,
                    Expense.expense_date <= current_date
                ).scalar() or 0

            # Calculate current month's projected ending balance
            running_balance = budget.monthly_amount - month_spent

            # For each month between current and target, add the monthly budget
            # (assuming zero spending in those future months)
            months_between = (target_month_date.year - current_month_date.year) * 12 + \
                           (target_month_date.month - current_month_date.month) - 1
            running_balance += budget.monthly_amount * months_between

            # IMPORTANT: running_balance now represents the balance carried INTO the target month
            # (i.e., the ending balance of the month before the target)
        elif is_current:
            # Calculate current month's spending
            month_start = current_month_date.replace(day=1).date()
            current_date = datetime.utcnow().date()

            if budget.user:
                month_spent = db.session.query(func.sum(Expense.amount)).filter(
                    Expense.category_id == budget.category_id,
                    Expense.created_by == budget.user,
                    Expense.expense_date >= month_start,
                    Expense.expense_date <= current_date
                ).scalar() or 0
            else:
                month_spent = db.session.query(func.sum(Expense.amount)).filter(
                    Expense.category_id == budget.category_id,
                    Expense.expense_date >= month_start,
                    Expense.expense_date <= current_date
                ).scalar() or 0

            running_balance = budget.monthly_amount - month_spent

    # Now calculate display for target month
    if is_current:
        # Current month: show actual spending
        month_start = current_month_date.replace(day=1).date()
        current_date = datetime.utcnow().date()

        if budget.user:
            current_spent = db.session.query(func.sum(Expense.amount)).filter(
                Expense.category_id == budget.category_id,
                Expense.created_by == budget.user,
                Expense.expense_date >= month_start,
                Expense.expense_date <= current_date
            ).scalar() or 0
        else:
            current_spent = db.session.query(func.sum(Expense.amount)).filter(
                Expense.category_id == budget.category_id,
                Expense.expense_date >= month_start,
                Expense.expense_date <= current_date
            ).scalar() or 0

        # Calculate starting balance for this month (from previous month's end)
        if last_snapshot:
            starting_balance = (last_snapshot.carried_surplus - last_snapshot.carried_deficit +
                               last_snapshot.monthly_amount - last_snapshot.actual_spent)
        else:
            starting_balance = 0

        # Apply display rules
        if starting_balance >= 0:
            effective_budget = budget.monthly_amount + starting_balance
            displayed_spent = current_spent
        else:
            effective_budget = budget.monthly_amount
            displayed_spent = current_spent + abs(starting_balance)

        remaining = effective_budget - displayed_spent

    else:  # is_future
        # Future month: assume zero spending in target month
        # running_balance represents the balance carried INTO this month

        # Apply display rules
        if running_balance >= 0:
            # Surplus: add to effective budget
            effective_budget = budget.monthly_amount + running_balance
            displayed_spent = 0
        else:
            # Deficit: show as already spent
            effective_budget = budget.monthly_amount
            displayed_spent = abs(running_balance)

        remaining = effective_budget - displayed_spent

    return {
        'id': budget.id,
        'category_id': budget.category_id,
        'category': budget.category.name,
        'parent_type': budget.category.parent_type,
        'user': budget.user,
        'monthly_amount': budget.monthly_amount,
        'effective_budget': effective_budget,
        'current_spent': displayed_spent,
        'remaining': remaining,
        'is_over_budget': remaining < 0
    }

# API Routes
@app.route('/api/expenses', methods=['GET'])
@auth.login_required
def get_expenses():
    username = auth.current_user()
    # Get expenses created by current user OR expenses with Shared category
    expenses = Expense.query.join(Category).filter(
        (Expense.created_by == username) | (Category.parent_type == 'Shared')
    ).all()
    return jsonify([expense.to_dict() for expense in expenses])

@app.route('/api/expenses', methods=['POST'])
@auth.login_required
def create_expense():
    from flask import request
    from datetime import datetime
    data = request.get_json()

    # Parse the date from ISO format if provided, otherwise use today
    expense_date = data.get('expense_date')
    if expense_date:
        expense_date = datetime.fromisoformat(expense_date).date()
    else:
        expense_date = datetime.utcnow().date()

    # Validate that a budget exists for this category
    expense_month = expense_date.strftime('%Y-%m')
    current_month = datetime.utcnow().strftime('%Y-%m')
    category_id = data.get('category_id')
    username = auth.current_user()

    # Get the category to check if it's personal or shared
    category = Category.query.get(category_id)
    if not category:
        return jsonify({'error': 'Category not found'}), 404

    # Find the budget for this category
    if category.parent_type == 'Personal':
        budget = Budget.query.filter_by(
            category_id=category_id,
            user=username
        ).first()
    else:
        budget = Budget.query.filter_by(
            category_id=category_id,
            user=None
        ).first()

    # If no budget exists, reject the expense
    if not budget:
        return jsonify({
            'error': f'No budget exists for this category.'
        }), 400

    # Create the expense
    expense = Expense(
        description=data.get('description', ''),
        amount=data.get('amount'),
        category_id=category_id,
        created_by=username,
        expense_date=expense_date
    )
    db.session.add(expense)
    db.session.commit()

    # If expense is in a past month, recalculate snapshots from that month forward
    if expense_month < current_month:
        # Check if a snapshot exists for this month
        snapshot = MonthlyBudgetSnapshot.query.filter_by(
            category_id=category_id,
            user=budget.user,
            month=expense_month
        ).first()

        if snapshot:
            # Snapshot exists, so we need to recalculate from this month forward
            recalculate_snapshots_from_month(budget, expense_month)

    return jsonify(expense.to_dict()), 201

@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@auth.login_required
def delete_expense(expense_id):
    from datetime import datetime

    username = auth.current_user()
    expense = Expense.query.get(expense_id)

    if not expense:
        return jsonify({'error': 'Expense not found'}), 404

    # Check permission: user can only delete their own expenses
    if expense.created_by != username:
        return jsonify({'error': 'You do not have permission to delete this expense'}), 403

    # Get expense details before deletion for snapshot recalculation
    expense_month = expense.expense_date.strftime('%Y-%m')
    current_month = datetime.utcnow().strftime('%Y-%m')
    category_id = expense.category_id
    category = expense.category

    # Find the budget for this category
    if category.parent_type == 'Personal':
        budget = Budget.query.filter_by(
            category_id=category_id,
            user=username
        ).first()
    else:
        budget = Budget.query.filter_by(
            category_id=category_id,
            user=None
        ).first()

    # Delete the expense
    db.session.delete(expense)
    db.session.commit()

    # If expense was in a past month, recalculate snapshots from that month forward
    if budget and expense_month < current_month:
        # Check if a snapshot exists for this month
        snapshot = MonthlyBudgetSnapshot.query.filter_by(
            category_id=category_id,
            user=budget.user,
            month=expense_month
        ).first()

        if snapshot:
            # Snapshot exists, so we need to recalculate from this month forward
            recalculate_snapshots_from_month(budget, expense_month)

    return jsonify({'message': 'Expense deleted successfully'}), 200

@app.route('/api/expenses/history', methods=['GET'])
@auth.login_required
def get_expense_history():
    """Get expense history grouped by month for the authenticated user.

    Query Parameters:
        months_back (optional): Number of months to fetch (default: 2)
    """
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    from flask import request

    username = auth.current_user()
    months_back = int(request.args.get('months_back', 2))

    # Calculate the date range
    current_date = datetime.utcnow()
    start_month = current_date - relativedelta(months=months_back - 1)
    start_date = start_month.replace(day=1).date()

    # Get expenses for current user (Personal) or Shared categories
    expenses = Expense.query.join(Category).filter(
        (Expense.created_by == username) | (Category.parent_type == 'Shared'),
        Expense.expense_date >= start_date
    ).order_by(Expense.expense_date.desc()).all()

    # Group expenses by month
    expenses_by_month = {}
    for expense in expenses:
        month_key = expense.expense_date.strftime('%Y-%m')
        if month_key not in expenses_by_month:
            expenses_by_month[month_key] = []
        expenses_by_month[month_key].append(expense.to_dict())

    # Convert to sorted list of months (most recent first)
    months_data = []
    for month_key in sorted(expenses_by_month.keys(), reverse=True):
        month_date = datetime.strptime(month_key, '%Y-%m')
        months_data.append({
            'month': month_key,
            'month_display': month_date.strftime('%B %Y'),
            'expenses': expenses_by_month[month_key],
            'total': sum(e['amount'] for e in expenses_by_month[month_key])
        })

    return jsonify({
        'months': months_data,
        'months_back': months_back
    })

@app.route('/api/categories', methods=['GET'])
@auth.login_required
def get_categories():
    categories = Category.query.all()
    return jsonify([category.to_dict() for category in categories])

@app.route('/api/budgets', methods=['GET'])
@auth.login_required
def get_budgets():
    """Get budget status for all categories visible to the authenticated user.

    Query Parameters:
        month (optional): Month in YYYY-MM format. Defaults to current month.
    """
    from datetime import datetime
    from flask import request

    username = auth.current_user()
    current_month_str = datetime.utcnow().strftime('%Y-%m')

    # Finalize previous months on first API call after month boundary
    finalize_previous_months()

    # Get optional month query parameter
    requested_month = request.args.get('month', current_month_str)

    # Validate month format
    try:
        datetime.strptime(requested_month, '%Y-%m')
    except ValueError:
        return jsonify({'error': f'Invalid month format: {requested_month}. Expected YYYY-MM'}), 400

    # Get budgets for current user (Personal categories) and Shared categories
    budgets = Budget.query.join(Category).filter(
        (Budget.user == username) | (Budget.user == None)
    ).all()

    budget_status = []

    for budget in budgets:
        status = get_budget_status_for_month(budget, requested_month, current_month_str)
        if status:  # None means no snapshot exists for past month
            budget_status.append(status)

    # Calculate aggregate summaries for Personal and Shared with asymmetric surplus/deficit rules
    personal_budgets = [b for b in budget_status if b['user'] is not None]
    shared_budgets = [b for b in budget_status if b['user'] is None]

    is_current_month = requested_month == current_month_str
    is_past_month = requested_month < current_month_str
    is_future_month = requested_month > current_month_str

    def calculate_aggregate_summary(category_budgets):
        """Calculate aggregate summary with asymmetric surplus/deficit rules."""
        if not category_budgets:
            return None

        # Sum up base monthly budgets (before any surplus/deficit adjustments)
        total_base_budget = sum(b['monthly_amount'] for b in category_budgets)

        if is_current_month:
            # Current month: Show actual total spending (no asymmetric rules at aggregate level)
            # We need to reverse-engineer the actual spending from the per-category displayed values
            # For categories: if they have deficit carried in, current_spent includes that deficit
            # We need to get the true spending by looking at the remaining values
            total_actual_spending = total_base_budget - sum(b['remaining'] for b in category_budgets)

            return {
                'base_budget': total_base_budget,
                'effective_budget': total_base_budget,
                'spent': total_actual_spending,
                'remaining': total_base_budget - total_actual_spending,
                'is_over_budget': total_actual_spending > total_base_budget
            }
        elif is_past_month:
            # Past month: Show historical data with asymmetric display
            # effective_budget already includes carried surplus
            # current_spent already includes carried deficit
            total_effective_budget = sum(b['effective_budget'] for b in category_budgets)
            total_displayed_spent = sum(b['current_spent'] for b in category_budgets)
            total_remaining = sum(b['remaining'] for b in category_budgets)

            return {
                'base_budget': total_base_budget,
                'effective_budget': total_effective_budget,
                'spent': total_displayed_spent,
                'remaining': total_remaining,
                'is_over_budget': total_remaining < 0
            }
        else:
            # Future month: Apply asymmetric rules at the aggregate level
            # Calculate the true net balance from base budget
            # remaining = effective_budget - displayed_spent
            # For surplus: effective_budget = monthly_amount + surplus, displayed_spent = 0
            #   so: remaining = monthly_amount + surplus, thus: net_balance = remaining - monthly_amount
            # For deficit: effective_budget = monthly_amount, displayed_spent = deficit
            #   so: remaining = monthly_amount - deficit, thus: net_balance = remaining - monthly_amount
            # In both cases: net_balance = remaining - monthly_amount
            net_balance = sum(b['remaining'] - b['monthly_amount'] for b in category_budgets)

            # Apply asymmetric rules at the aggregate level
            if net_balance >= 0:
                # Surplus: add to effective budget, show actual spending as 0 for future months
                effective_budget = total_base_budget + net_balance
                displayed_spent = 0
                remaining = effective_budget  # Same as net_balance + total_base_budget
            else:
                # Deficit: keep base budget, show deficit as spending
                effective_budget = total_base_budget
                displayed_spent = abs(net_balance)
                remaining = effective_budget - displayed_spent  # Positive value showing what's left

            return {
                'base_budget': total_base_budget,
                'effective_budget': effective_budget,
                'spent': displayed_spent,
                'remaining': remaining,
                'is_over_budget': remaining < 0
            }

    personal_summary = calculate_aggregate_summary(personal_budgets)
    shared_summary = calculate_aggregate_summary(shared_budgets)

    return jsonify({
        'categories': budget_status,
        'personal_summary': personal_summary,
        'shared_summary': shared_summary
    })

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)

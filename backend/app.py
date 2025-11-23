from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_migrate import Migrate
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
import os
from dotenv import load_dotenv
from models import db, Expense, Category, Budget

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "*", "allow_headers": ["Content-Type", "Authorization"]}})
auth = HTTPBasicAuth()

# Database configuration
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

    current_month = datetime.utcnow().strftime('%Y-%m')

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
                monthly_amount=monthly_amount,
                cumulative_balance=0,
                last_updated_month=current_month
            )
            budgets.append(budget)

    db.session.add_all(budgets)
    db.session.commit()
    print(f"Seeded {len(budgets)} budgets for current month {current_month}")

@app.cli.command('seed-budgets')
def seed_budgets_command():
    """Seed the database with initial budgets."""
    with app.app_context():
        if Budget.query.count() == 0:
            seed_budgets()
        else:
            print("Budgets already exist, skipping seed")

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

    # Validate that a budget exists for this category and month
    expense_month = expense_date.strftime('%Y-%m')
    current_month = datetime.utcnow().strftime('%Y-%m')
    category_id = data.get('category_id')
    username = auth.current_user()

    # Get the category to check if it's personal or shared
    category = Category.query.get(category_id)
    if not category:
        return jsonify({'error': 'Category not found'}), 404

    # Find the budget for this category and month
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

    # If no budget exists, reject expenses for past months
    if not budget:
        if expense_month < current_month:
            return jsonify({
                'error': f'Cannot add expense to past month {expense_month}. No budget exists for this category.'
            }), 400

    # If budget exists but hasn't been updated to this month yet, check if it's a past month
    if budget and budget.last_updated_month < expense_month < current_month:
        return jsonify({
            'error': f'Cannot add expense to past month {expense_month}. Budget has not been created for this month.'
        }), 400

    expense = Expense(
        description=data.get('description', ''),
        amount=data.get('amount'),
        category_id=category_id,
        created_by=username,
        expense_date=expense_date
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify(expense.to_dict()), 201

@app.route('/api/categories', methods=['GET'])
@auth.login_required
def get_categories():
    categories = Category.query.all()
    return jsonify([category.to_dict() for category in categories])

@app.route('/api/budgets', methods=['GET'])
@auth.login_required
def get_budgets():
    """Get budget status for all categories visible to the authenticated user."""
    from datetime import datetime
    from dateutil.relativedelta import relativedelta
    from sqlalchemy import func

    username = auth.current_user()
    current_month_str = datetime.utcnow().strftime('%Y-%m')
    current_date = datetime.utcnow().date()

    # Get budgets for current user (Personal categories) and Shared categories
    budgets = Budget.query.join(Category).filter(
        (Budget.user == username) | (Budget.user == None)
    ).all()

    budget_status = []

    for budget in budgets:
        # Update budget if we've crossed into a new month
        if budget.last_updated_month != current_month_str:
            # Calculate how many months have elapsed
            last_updated = datetime.strptime(budget.last_updated_month, '%Y-%m')
            current_month_date = datetime.strptime(current_month_str, '%Y-%m')

            # Process each elapsed month
            temp_date = last_updated
            while temp_date < current_month_date:
                month_str = temp_date.strftime('%Y-%m')

                # Get spending for that month
                month_start = temp_date.replace(day=1).date()
                next_month = temp_date + relativedelta(months=1)
                month_end = next_month.replace(day=1).date()

                # Query expenses for this budget in this month
                if budget.user:
                    # Personal budget: only expenses by this user
                    spent = db.session.query(func.sum(Expense.amount)).filter(
                        Expense.category_id == budget.category_id,
                        Expense.created_by == budget.user,
                        Expense.expense_date >= month_start,
                        Expense.expense_date < month_end
                    ).scalar() or 0
                else:
                    # Shared budget: all expenses in this category
                    spent = db.session.query(func.sum(Expense.amount)).filter(
                        Expense.category_id == budget.category_id,
                        Expense.expense_date >= month_start,
                        Expense.expense_date < month_end
                    ).scalar() or 0

                # Add to cumulative balance: (budget - spent)
                budget.cumulative_balance += (budget.monthly_amount - spent)

                # Move to next month
                temp_date = next_month

            # Update last_updated_month
            budget.last_updated_month = current_month_str
            db.session.commit()

        # Calculate current month's spending
        month_start = datetime.strptime(current_month_str, '%Y-%m').replace(day=1).date()

        if budget.user:
            # Personal budget
            current_spent = db.session.query(func.sum(Expense.amount)).filter(
                Expense.category_id == budget.category_id,
                Expense.created_by == budget.user,
                Expense.expense_date >= month_start,
                Expense.expense_date <= current_date
            ).scalar() or 0
        else:
            # Shared budget
            current_spent = db.session.query(func.sum(Expense.amount)).filter(
                Expense.category_id == budget.category_id,
                Expense.expense_date >= month_start,
                Expense.expense_date <= current_date
            ).scalar() or 0

        # Calculate effective budget for current month
        effective_budget = budget.monthly_amount + budget.cumulative_balance
        remaining = effective_budget - current_spent

        budget_status.append({
            'id': budget.id,
            'category_id': budget.category_id,
            'category': budget.category.name,
            'parent_type': budget.category.parent_type,
            'user': budget.user,
            'monthly_amount': budget.monthly_amount,
            'cumulative_balance': budget.cumulative_balance,
            'effective_budget': effective_budget,
            'current_spent': current_spent,
            'remaining': remaining,
            'is_over_budget': remaining < 0
        })

    return jsonify(budget_status)

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

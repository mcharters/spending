from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_migrate import Migrate
import os
from models import db, Expense, Category

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Database configuration
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

# Seed categories function (call after running migrations)
def seed_categories():
    """Seed initial categories. Run with: flask seed-categories"""
    categories = [
        # Personal categories
        Category(name='Beauty', parent_type='Personal'),
        Category(name='Clothing', parent_type='Personal'),
        Category(name='Counselling', parent_type='Personal'),
        Category(name='Entertainment', parent_type='Personal'),
        Category(name='Media', parent_type='Personal'),
        Category(name='Misc', parent_type='Personal'),
        Category(name='Workouts', parent_type='Personal'),

        # Shared categories
        Category(name='Car', parent_type='Shared'),
        Category(name='Dining', parent_type='Shared'),
        Category(name='Groceries', parent_type='Shared'),
        Category(name='House', parent_type='Shared'),
        Category(name='Kids', parent_type='Shared'),
        Category(name='Outings', parent_type='Shared'),
        Category(name='Utilities', parent_type='Shared'),
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

# API Routes
@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    expenses = Expense.query.all()
    return jsonify([expense.to_dict() for expense in expenses])

@app.route('/api/expenses', methods=['POST'])
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

    expense = Expense(
        description=data.get('description'),
        amount=data.get('amount'),
        category_id=data.get('category_id'),
        expense_date=expense_date
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify(expense.to_dict()), 201

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify([category.to_dict() for category in categories])

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

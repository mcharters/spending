from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    parent_type = db.Column(db.String(20), nullable=False)  # "Personal" or "Shared"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'parent_type': self.parent_type
        }

    def __repr__(self):
        return f'<Category {self.name} ({self.parent_type})>'

class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=True)
    amount = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    created_by = db.Column(db.String(50), nullable=False)
    expense_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Category
    category = db.relationship('Category', backref='expenses')

    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'amount': self.amount,
            'category': self.category.name,
            'category_id': self.category_id,
            'parent_type': self.category.parent_type,
            'created_by': self.created_by,
            'expense_date': self.expense_date.isoformat(),
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<Expense {self.description}: ${self.amount}>'

class Budget(db.Model):
    __tablename__ = 'budgets'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    user = db.Column(db.String(50), nullable=True)  # null for Shared categories, username for Personal
    monthly_amount = db.Column(db.Float, nullable=False)
    cumulative_balance = db.Column(db.Float, default=0)
    last_updated_month = db.Column(db.String(7), nullable=False)  # "YYYY-MM" format
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Category
    category = db.relationship('Category', backref='budgets')

    # Unique constraint: one budget per (category_id, user) combination
    __table_args__ = (
        db.UniqueConstraint('category_id', 'user', name='unique_category_user_budget'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'category_id': self.category_id,
            'category': self.category.name,
            'parent_type': self.category.parent_type,
            'user': self.user,
            'monthly_amount': self.monthly_amount,
            'cumulative_balance': self.cumulative_balance,
            'last_updated_month': self.last_updated_month,
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        user_str = self.user if self.user else 'shared'
        return f'<Budget {self.category.name} ({user_str}): ${self.monthly_amount}/month>'

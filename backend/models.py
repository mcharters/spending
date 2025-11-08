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
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
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
            'created_at': self.created_at.isoformat()
        }

    def __repr__(self):
        return f'<Expense {self.description}: ${self.amount}>'

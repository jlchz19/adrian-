from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    income_sources = db.relationship('IncomeSource', backref='user', lazy=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class IncomeSource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False) # e.g. "Sueldo Quincena", "Venta Carro"
    currency = db.Column(db.String(50), nullable=False) # Bolivares, Dolares Efectivo, Zelle, Binance
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('Transaction', backref='source', lazy=True)
    
    @property
    def remaining_amount(self):
        total_in = sum(t.amount for t in self.transactions if t.type in ['ingreso_nuevo', 'ingreso_adicional'])
        total_out = sum(t.amount for t in self.transactions if t.type == 'egreso')
        return total_in - total_out

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    source_id = db.Column(db.Integer, db.ForeignKey('income_source.id'), nullable=False)
    type = db.Column(db.String(30), nullable=False) # 'ingreso_nuevo', 'ingreso_adicional', 'egreso'
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    time = db.Column(db.Time, nullable=False, default=datetime.utcnow().time)

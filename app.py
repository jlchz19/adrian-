from flask import Flask, render_template, redirect, url_for, flash, request, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Transaction, IncomeSource
from datetime import datetime
import os
from utils.pdf_generator import generate_pdf_report

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

with app.app_context():
    db.create_all()

CATEGORIAS_REPORTES = {
    'Vehículo': {
        'keywords': ['carro', 'auto', 'gasolina', 'taller', 'vehículo', 'vehiculo', 'repuesto', 'moto'],
        'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg>'
    },
    'Divisas': {
        'keywords': ['dolar', 'dólar', 'dolares', 'dólares', 'divisa', 'divisas', 'euro', 'euros', 'cambio', 'zelle'],
        'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>'
    },
    'Comida': {
        'keywords': ['comida', 'supermercado', 'restaurante', 'cena', 'almuerzo', 'desayuno', 'mercado', 'pizza', 'hamburguesa'],
        'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8h1a4 4 0 0 1 0 8h-1"></path><path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"></path><line x1="6" y1="1" x2="6" y2="4"></line><line x1="10" y1="1" x2="10" y2="4"></line><line x1="14" y1="1" x2="14" y2="4"></line></svg>'
    },
    'Servicios': {
        'keywords': ['luz', 'agua', 'internet', 'teléfono', 'telefono', 'gas', 'alquiler', 'renta', 'servicio'],
        'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.55a11 11 0 0 1 14.08 0"></path><path d="M1.42 9a16 16 0 0 1 21.16 0"></path><path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path><line x1="12" y1="20" x2="12.01" y2="20"></line></svg>'
    }
}

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Usuario o contraseña incorrectos', 'error')
    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('El usuario ya existe', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('El correo ya está registrado', 'error')
            return redirect(url_for('register'))
            
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registro exitoso. Puedes iniciar sesión.', 'success')
        return redirect(url_for('login'))
        
    return render_template('auth/register.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            print(f"[SIMULACIÓN] Correo de recuperación enviado a: {email}")
            flash('Si el correo existe, se han enviado las instrucciones de recuperación.', 'info')
        else:
            flash('Si el correo existe, se han enviado las instrucciones de recuperación.', 'info')
        return redirect(url_for('login'))
    return render_template('auth/reset_password.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/calculator')
@login_required
def calculator():
    return render_template('calculator.html')

@app.route('/reports')
@login_required
def reports():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    
    active_categories = {}
    for cat_name, data in CATEGORIAS_REPORTES.items():
        count = sum(1 for t in transactions if any(kw in t.description.lower() for kw in data['keywords']))
        if count > 0:
            active_categories[cat_name] = {
                'icon': data['icon'],
                'count': count
            }
            
    return render_template('reports.html', active_categories=active_categories)

@app.route('/dashboard')
@login_required
def dashboard():
    sources = IncomeSource.query.filter_by(user_id=current_user.id).all()
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc(), Transaction.time.desc()).limit(50).all()
    
    total_disponible = sum(s.remaining_amount for s in sources)
    
    # Agrupar por método para el gráfico basado en el saldo restante
    metodos = {}
    for s in sources:
        if s.currency not in metodos:
            metodos[s.currency] = 0
        metodos[s.currency] += s.remaining_amount
        
    return render_template('dashboard.html', 
                           sources=sources,
                           transactions=transactions,
                           total_disponible=total_disponible,
                           metodos=metodos)

@app.route('/transaction/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    if request.method == 'POST':
        operation_type = request.form.get('operation_type') # ingreso_nuevo, ingreso_adicional, egreso
        amount = float(request.form.get('amount'))
        description = request.form.get('description')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()
        time_obj = datetime.strptime(time_str, '%H:%M').time() if time_str else datetime.utcnow().time()

        if operation_type == 'ingreso_nuevo':
            source_name = request.form.get('source_name')
            currency = request.form.get('currency')
            
            new_source = IncomeSource(user_id=current_user.id, name=source_name, currency=currency)
            db.session.add(new_source)
            db.session.flush() # Para obtener el ID del source
            
            new_tx = Transaction(
                user_id=current_user.id,
                source_id=new_source.id,
                type='ingreso_nuevo',
                amount=amount,
                description=description,
                date=date_obj,
                time=time_obj
            )
            db.session.add(new_tx)
            
        elif operation_type == 'ingreso_adicional':
            source_id = int(request.form.get('source_id'))
            new_tx = Transaction(
                user_id=current_user.id,
                source_id=source_id,
                type='ingreso_adicional',
                amount=amount,
                description=description,
                date=date_obj,
                time=time_obj
            )
            db.session.add(new_tx)
            
        elif operation_type == 'egreso':
            source_id = int(request.form.get('source_id'))
            source = IncomeSource.query.get(source_id)
            if source.remaining_amount < amount:
                flash(f'No hay saldo suficiente en el bolsillo {source.name}', 'error')
                return redirect(url_for('add_transaction'))
                
            new_tx = Transaction(
                user_id=current_user.id,
                source_id=source_id,
                type='egreso',
                amount=amount,
                description=description,
                date=date_obj,
                time=time_obj
            )
            db.session.add(new_tx)

        db.session.commit()
        flash('Operación registrada exitosamente', 'success')
        return redirect(url_for('dashboard'))
        
    sources = IncomeSource.query.filter_by(user_id=current_user.id).all()
    # Solo fuentes con saldo positivo para egresos
    active_sources = [s for s in sources if s.remaining_amount > 0]
    
    return render_template('transactions/add.html', sources=sources, active_sources=active_sources)

@app.route('/transaction/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    tx = Transaction.query.get_or_404(id)
    if tx.user_id != current_user.id:
        flash('No tienes permiso para editar esta operación.', 'error')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        new_amount = float(request.form.get('amount'))
        description = request.form.get('description')
        date_str = request.form.get('date')
        time_str = request.form.get('time')
        
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else tx.date
        time_obj = datetime.strptime(time_str, '%H:%M').time() if time_str else tx.time
        
        # Validar saldos al cambiar montos
        source = tx.source
        if tx.type == 'egreso':
            # Si es un egreso, el nuevo monto no debe sobregirar el bolsillo
            balance_sin_este_egreso = source.remaining_amount + tx.amount
            if new_amount > balance_sin_este_egreso:
                flash(f'El nuevo monto excede el saldo disponible en el bolsillo "{source.name}".', 'error')
                return redirect(url_for('edit_transaction', id=id))
        else:
            # Si es un ingreso, si se reduce el monto, no debe dejar el bolsillo en negativo (por egresos existentes)
            balance_sin_este_ingreso = source.remaining_amount - tx.amount
            if balance_sin_este_ingreso + new_amount < 0:
                flash(f'No puedes reducir tanto este ingreso porque ya has gastado dinero de este bolsillo.', 'error')
                return redirect(url_for('edit_transaction', id=id))

        tx.amount = new_amount
        tx.description = description
        tx.date = date_obj
        tx.time = time_obj
        
        db.session.commit()
        flash('Operación actualizada exitosamente.', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('transactions/edit.html', tx=tx)

@app.route('/transaction/delete/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    tx = Transaction.query.get_or_404(id)
    if tx.user_id != current_user.id:
        flash('No tienes permiso para eliminar esta operación.', 'error')
        return redirect(url_for('dashboard'))
        
    db.session.delete(tx)
    db.session.commit()
    flash('Operación eliminada exitosamente.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/source/delete/<int:id>', methods=['POST'])
@login_required
def delete_source(id):
    source = IncomeSource.query.get_or_404(id)
    if source.user_id != current_user.id:
        flash('No tienes permiso para eliminar este bolsillo.', 'error')
        return redirect(url_for('dashboard'))
        
    # Eliminar todas las transacciones asociadas a este bolsillo primero
    Transaction.query.filter_by(source_id=source.id).delete()
    db.session.delete(source)
    db.session.commit()
    flash(f'Bolsillo "{source.name}" eliminado exitosamente.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/export/pdf')
@login_required
def export_pdf():
    category = request.args.get('category')
    transactions_query = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc(), Transaction.time.desc())
    
    if category and category in CATEGORIAS_REPORTES:
        keywords = CATEGORIAS_REPORTES[category]['keywords']
        all_txs = transactions_query.all()
        transactions = [t for t in all_txs if any(kw in t.description.lower() for kw in keywords)]
    else:
        transactions = transactions_query.all()
        
    sources = IncomeSource.query.filter_by(user_id=current_user.id).all()
    pdf_path = generate_pdf_report(current_user, sources, transactions, category)
    
    cat_name = category.replace(' ', '_') if category else "General"
    filename = f'Resumen_{cat_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    return send_file(pdf_path, as_attachment=True, download_name=filename, max_age=0)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)

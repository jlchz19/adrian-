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
    sources = IncomeSource.query.filter_by(user_id=current_user.id).all()
    transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc(), Transaction.time.desc()).all()
    pdf_path = generate_pdf_report(current_user, sources, transactions)
    return send_file(pdf_path, as_attachment=True, download_name='Resumen_Bolsillos.pdf')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)

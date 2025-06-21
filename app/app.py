import os
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
    UserMixin,
)

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'admin' or 'franchisee'

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    before_image = db.Column(db.String(150))
    after_image = db.Column(db.String(150))
    proof_image = db.Column(db.String(150))
    address = db.Column(db.String(150))
    zip_code = db.Column(db.String(10))
    customer_first = db.Column(db.String(150))
    customer_last = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    payment_method = db.Column(db.String(20))
    price = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(150))
    scheduled_for = db.Column(db.Date)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_first_request
def create_tables():
    db.create_all()
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', password='admin', role='admin')
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            login_user(user)
            return redirect(url_for('index'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'franchisee':
        return redirect(url_for('admin_dashboard'))
    sales = Sale.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', sales=sales)


@app.route('/calendar')
@login_required
def calendar():
    if current_user.role != 'franchisee':
        return redirect(url_for('admin_dashboard'))
    today = datetime.utcnow().date()
    next_week = today + timedelta(days=7)
    jobs = Job.query.filter(
        Job.user_id == current_user.id,
        Job.scheduled_for >= today,
        Job.scheduled_for <= next_week,
    ).all()
    return render_template('calendar.html', jobs=jobs)


@app.route('/performance')
@login_required
def performance():
    if current_user.role != 'franchisee':
        return redirect(url_for('admin_dashboard'))
    sales = Sale.query.filter_by(user_id=current_user.id).all()
    total = sum(s.price for s in sales if s.price)
    count = len(sales)
    avg = total / count if count else 0
    return render_template(
        'performance.html', total=total, count=count, average=avg
    )

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    sales = Sale.query.all()
    total = sum(s.price for s in sales if s.price)
    return render_template('admin_dashboard.html', sales=sales, total=total)

@app.route('/sale/new', methods=['GET', 'POST'])
@login_required
def new_sale():
    if current_user.role != 'franchisee':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        description = request.form['description']
        address = request.form['address']
        zip_code = request.form['zip_code']
        first = request.form['customer_first']
        last = request.form['customer_last']
        phone = request.form['phone']
        payment_method = request.form['payment_method']
        price = request.form['price']
        before_file = request.files['before_image']
        after_file = request.files['after_image']
        proof_file = request.files['proof_image']

        def save_file(f):
            if f and f.filename:
                path = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
                f.save(path)
                return f.filename
            return None

        before_filename = save_file(before_file)
        after_filename = save_file(after_file)
        proof_filename = save_file(proof_file)
        sale = Sale(
            user_id=current_user.id,
            description=description,
            address=address,
            zip_code=zip_code,
            customer_first=first,
            customer_last=last,
            phone=phone,
            payment_method=payment_method,
            price=float(price) if price else 0,
            before_image=before_filename,
            after_image=after_filename,
            proof_image=proof_filename,
        )
        db.session.add(sale)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('sale_form.html')

if __name__ == '__main__':
    app.run(debug=True)

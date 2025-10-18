import os
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import openai
from functools import wraps

# ---- App Config ----
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///saas_hub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---- AI Config ----
openai.api_key = os.getenv("OPENAI_API_KEY")  # Put your OpenAI key here

# ---- Models ----
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subscription_active = db.Column(db.Boolean, default=False)
    users = db.relationship('User', backref='company', lazy=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    is_admin = db.Column(db.Boolean, default=False)

class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    content = db.Column(db.Text)
    ai_feedback = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=db.func.now())

# ---- Login Loader ----
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---- Decorators ----
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

# ---- Routes ----
@app.route('/')
def index():
    return render_template('index.html')

# --- Company Registration ---
@app.route('/register_company', methods=['GET', 'POST'])
def register_company():
    if request.method == 'POST':
        company_name = request.form.get('company_name')
        admin_email = request.form.get('email')
        admin_password = request.form.get('password')

        if Company.query.filter_by(name=company_name).first():
            flash("Company already exists.", "danger")
            return redirect(url_for('register_company'))

        company = Company(name=company_name)
        db.session.add(company)
        db.session.commit()

        hashed_pw = generate_password_hash(admin_password)
        admin_user = User(email=admin_email, password=hashed_pw, company_id=company.id, is_admin=True)
        db.session.add(admin_user)
        db.session.commit()

        flash("Company registered! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register_company.html')

# --- Login / Logout ---
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials.", "danger")

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for('index'))

# --- Dashboard ---
@app.route('/dashboard')
@login_required
def dashboard():
    company_users = User.query.filter_by(company_id=current_user.company_id).all()
    interactions = Interaction.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', users=company_users, interactions=interactions)

# --- AI Assistant ---
@app.route('/assistant', methods=['GET','POST'])
@login_required
def assistant():
    feedback = None
    if request.method == 'POST':
        user_input = request.form.get('message')
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_input}]
        )
        feedback = response['choices'][0]['message']['content']

        inter = Interaction(user_id=current_user.id, content=user_input, ai_feedback=feedback)
        db.session.add(inter)
        db.session.commit()

    return render_template('assistant.html', feedback=feedback)

# --- Admin Analytics (Company-Level) ---
@app.route('/analytics')
@login_required
@admin_required
def analytics():
    company_users = User.query.filter_by(company_id=current_user.company_id).all()
    interactions = Interaction.query.join(User).filter(User.company_id==current_user.company_id).all()
    return render_template('analytics.html', users=company_users, interactions=interactions)

# ---- Run App ----
if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import openai
import stripe

# ---- App Config ----
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///saas_hub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---- OpenAI Config ----
openai.api_key = os.getenv("OPENAI_API_KEY")

# ---- Stripe Config ----
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
DOMAIN_URL = os.getenv("DOMAIN_URL", "http://localhost:5000")

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

# ---- Routes ----
@app.route('/')
def index():
    return render_template('index.html')

# ----- AI Assistant -----
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

# ----- Stripe Billing Routes -----
@app.route('/subscribe', methods=['GET'])
@login_required
def subscribe():
    try:
        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=['card'],
            line_items=[{
                'price': os.getenv("STRIPE_PRICE_ID"),  # set in Stripe dashboard
                'quantity': 1
            }],
            mode='subscription',
            success_url=DOMAIN_URL + '/subscription-success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=DOMAIN_URL + '/subscription-cancel'
        )
        return redirect(checkout_session.url)
    except Exception as e:
        return str(e)

@app.route('/subscription-success')
@login_required
def subscription_success():
    # mark user's company as subscribed
    if current_user.company:
        current_user.company.subscription_active = True
        db.session.commit()
    flash("Subscription successful! Your company now has full access.", "success")
    return redirect(url_for('dashboard'))

@app.route('/subscription-cancel')
@login_required
def subscription_cancel():
    flash("Subscription canceled or failed. Try again.", "warning")
    return redirect(url_for('index'))

# ----- Company Dashboard (Multi-Tenant) -----
@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.company or not current_user.company.subscription_active:
        flash("Your company does not have an active subscription. Please subscribe.", "warning")
        return redirect(url_for('index'))
    # Placeholder for analytics and data
    users = User.query.filter_by(company_id=current_user.company.id).all()
    interactions = Interaction.query.join(User, Interaction.user_id==User.id)\
                    .filter(User.company_id==current_user.company.id).all()
    return render_template('dashboard.html', users=users, interactions=interactions)

# ----- AI-Powered Analytics (Placeholder) -----
@app.route('/analytics')
@login_required
def analytics():
    # Only for admin users
    if not current_user.is_admin:
        flash("Admins only", "danger")
        return redirect(url_for('index'))
    
    # Example analytics: top users by AI interactions
    top_users = db.session.query(User.email, db.func.count(Interaction.id).label('interaction_count'))\
                 .join(Interaction, Interaction.user_id==User.id)\
                 .group_by(User.id).order_by(db.desc('interaction_count')).all()
    return render_template('analytics.html', top_users=top_users)

# ----- Placeholder Login / Signup -----
@app.route('/login')
def login():
    return "Login page placeholder. Coming soon!"

@app.route('/signup')
def signup():
    return "Signup page placeholder. Coming soon!"

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for('index'))

# ---- Main ----
if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)

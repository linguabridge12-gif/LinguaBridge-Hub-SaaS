import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import requests
import json
import openai

# ---- App Config ----
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///saas_hub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---- AI Config ----
openai.api_key = os.getenv("OPENAI_API_KEY")

# ---- PayPal Config ----
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")
DOMAIN_URL = os.getenv("DOMAIN_URL")

# Get PayPal access token
def get_paypal_token():
    url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"
    auth = (PAYPAL_CLIENT_ID, PAYPAL_SECRET)
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    data = {"grant_type": "client_credentials"}
    r = requests.post(url, headers=headers, data=data, auth=auth)
    return r.json().get("access_token")

# ---- Models ----
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subscription_active = db.Column(db.Boolean, default=False)
    users = db.relationship('User', backref='company')

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

@app.route('/dashboard')
@login_required
def dashboard():
    company_users = User.query.filter_by(company_id=current_user.company_id).all()
    interactions = Interaction.query.filter(Interaction.user_id.in_([u.id for u in company_users])).all()
    return render_template('dashboard.html', users=company_users, interactions=interactions)

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

@app.route('/subscribe')
@login_required
def subscribe():
    access_token = get_paypal_token()
    # PayPal subscription URL (replace PLAN_ID with your actual plan ID)
    plan_id = "P-XXXXXXXXXXXXXXXXX"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        "plan_id": plan_id,
        "subscriber": {
            "name": {"given_name": current_user.email.split("@")[0], "surname": ""},
            "email_address": current_user.email
        },
        "application_context": {
            "brand_name": "LinguaBridge Hub SaaS",
            "return_url": f"{DOMAIN_URL}/subscription-success",
            "cancel_url": f"{DOMAIN_URL}/subscription-cancel"
        }
    }
    r = requests.post("https://api-m.sandbox.paypal.com/v1/billing/subscriptions",
                      headers=headers, json=data)
    subscription = r.json()
    approval_url = next((link['href'] for link in subscription['links'] if link['rel']=="approve"), None)
    return redirect(approval_url)

@app.route('/subscription-success')
@login_required
def subscription_success():
    current_user.company.subscription_active = True
    db.session.commit()
    flash("Subscription active! 🎉", "success")
    return redirect(url_for('dashboard'))

@app.route('/subscription-cancel')
@login_required
def subscription_cancel():
    flash("Subscription cancelled or failed.", "error")
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)

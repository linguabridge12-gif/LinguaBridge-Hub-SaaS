import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
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
openai.api_key = os.getenv("OPENAI_API_KEY")  # Put your OpenAI key here

# ---- Models ----
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subscription_active = db.Column(db.Boolean, default=False)

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

@app.route('/assistant', methods=['GET','POST'])
@login_required
def assistant():
    feedback = None
    if request.method == 'POST':
        user_input = request.form.get('message')
        # Real AI call
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_input}]
        )
        feedback = response['choices'][0]['message']['content']

        # Save to DB
        inter = Interaction(user_id=current_user.id, content=user_input, ai_feedback=feedback)
        db.session.add(inter)
        db.session.commit()
    return render_template('assistant.html', feedback=feedback)

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
@app.route('/login')
def login():
    return "Login page placeholder. Coming soon!"

@app.route('/signup')
def signup():
    return "Signup page placeholder. Coming soon!"

@app.route('/logout')
def logout():
    return "Logout page placeholder. Coming soon!"

# saas_app.py
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import openai
from datetime import datetime
from sqlalchemy import func

# ---- App Config ----
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///saas_hub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ---- AI Config ----
openai.api_key = os.getenv("OPENAI_API_KEY")  # Put your OpenAI key in Render environment

# ---- Models ----
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subscription_active = db.Column(db.Boolean, default=False)
    users = db.relationship("User", backref="company")

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
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

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
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": user_input}]
        )
        feedback = response['choices'][0]['message']['content']

        # Save user interaction
        interaction = Interaction(user_id=current_user.id, content=user_input, ai_feedback=feedback)
        db.session.add(interaction)
        db.session.commit()
    return render_template('assistant.html', feedback=feedback)

# ---- Multi-Tenant Dashboard ----
@app.route('/dashboard')
@login_required
def dashboard():
    company_id = current_user.company_id
    if not company_id:
        flash("You are not assigned to a company yet.", "warning")
        return redirect(url_for('index'))

    # Company users
    users = User.query.filter_by(company_id=company_id).all()
    total_users = len(users)

    # Company interactions
    interactions = Interaction.query.join(User, Interaction.user_id==User.id)\
        .filter(User.company_id==company_id).all()
    total_interactions = len(interactions)

    # Prepare AI analytics summary
    analytics_summary = None
    if interactions:
        combined_content = "\n".join([i.content for i in interactions])
        try:
            summary_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": f"Analyze these interactions and summarize key trends:\n{combined_content}"}]
            )
            analytics_summary = summary_response['choices'][0]['message']['content']
        except Exception as e:
            analytics_summary = f"AI analytics failed: {str(e)}"

    return render_template('dashboard.html',
                           total_users=total_users,
                           total_interactions=total_interactions,
                           analytics_summary=analytics_summary)

# ---- Auth placeholders ----
@app.route('/login')
def login():
    return "Login page placeholder. Coming soon!"

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# ---- Run App ----
if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)

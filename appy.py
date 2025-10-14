# appy.py (FULL INTEGRATED VERSION)

import os
import json
from datetime import datetime
from flask import (Flask, render_template, jsonify, request, redirect,
                   url_for, flash, abort)
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (LoginManager, UserMixin, login_user,
                         login_required, logout_user, current_user)
from sqlalchemy import func
from functools import wraps

# ---- App config ----
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///linguabridge.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login_view'

# ---- Models ----
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password = db.Column(db.String(300), nullable=False)
    subscription_status = db.Column(db.String(50), default="inactive")
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, nullable=False)
    progress = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    lesson_id = db.Column(db.Integer, nullable=True)
    event_type = db.Column(db.String(100), nullable=False)
    meta = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CoachingRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    message = db.Column(db.Text)
    status = db.Column(db.String(50), default="new")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LocalizationFeedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    lesson_id = db.Column(db.Integer, nullable=False)
    locale = db.Column(db.String(20), nullable=True)
    comment = db.Column(db.Text)
    rating = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---- Login loader ----
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---- Admin decorator ----
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return fn(*args, **kwargs)
    return wrapper

# ---- Lessons data ----
lessons = []
core_lessons = [
    (1, "Intro to Spanish", "Greetings, basic phrases, pronunciation, and cultural notes in Spanish.", "Hello in Spanish?", "Hola"),
    (2, "Intro to French", "Greetings, basic phrases, pronunciation, and cultural notes in French.", "Thank you in French?", "Merci"),
    (3, "Intro to German", "Greetings, basic phrases, pronunciation, and cultural notes in German.", "Good morning in German?", "Guten Morgen"),
    (4, "Intro to Italian", "Greetings, basic phrases, pronunciation, and cultural notes in Italian.", "Goodbye in Italian?", "Arrivederci")
]
for id_, title, content, q, a in core_lessons:
    lessons.append({
        "id": id_,
        "title": title,
        "content": content,
        "quiz": [{"question": q, "answer": a}]
    })
for i in range(5, 121):
    lessons.append({
        "id": i,
        "title": f"Module {i}",
        "content": f"Module {i} covers advanced language concepts, exercises, listening practice, and conversation scenarios.",
        "quiz": [{"question": f"Key concept of Module {i}?", "answer": f"Answer {i}"}]
    })

def get_lesson_by_id(lesson_id):
    return next((l for l in lessons if l['id'] == lesson_id), None)

# ---- Routes ----

@app.route('/')
def index():
    preview = lessons[:6]  # Show first 6 lessons
    return render_template('index.html', lessons=preview, full_count=len(lessons))

@app.route('/lessons')
@login_required
def all_lessons():
    return render_template('lessons.html', lessons=lessons)

@app.route('/lesson/<int:lesson_id>')
@login_required
def lesson(lesson_id):
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        abort(404)
    # Only allow enrolled users to see full content
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, lesson_id=lesson_id).first()
    if not enrollment:
        flash("Please enroll to access full lesson.", "warning")
        return redirect(url_for('all_lessons'))
    ev = Event(user_id=current_user.id, lesson_id=lesson_id, event_type='view_lesson')
    db.session.add(ev)
    db.session.commit()
    return render_template('lesson_detail_full.html', lesson=lesson)

@app.route('/enroll/<int:lesson_id>', methods=['POST'])
@login_required
def enroll(lesson_id):
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        abort(404)
    existing = Enrollment.query.filter_by(user_id=current_user.id, lesson_id=lesson_id).first()
    if existing:
        flash("Already enrolled.", "info")
        return redirect(url_for('lesson', lesson_id=lesson_id))
    e = Enrollment(user_id=current_user.id, lesson_id=lesson_id)
    db.session.add(e)
    db.session.commit()
    flash("Enrolled successfully!", "success")
    return redirect(url_for('lesson', lesson_id=lesson_id))

@app.route('/coach', methods=['GET','POST'])
def coach():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        cr = CoachingRequest(user_id=current_user.get_id() if current_user.is_authenticated else None,
                             name=name, email=email, message=message)
        db.session.add(cr)
        db.session.commit()
        flash("Coaching request submitted.", "success")
        return redirect(url_for('index'))
    return render_template('coach.html')

@app.route('/feedback/<int:lesson_id>', methods=['GET','POST'])
def feedback(lesson_id):
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        abort(404)
    if request.method == 'POST':
        locale = request.form.get('locale')
        comment = request.form.get('comment')
        rating = request.form.get('rating', type=int)
        fb = LocalizationFeedback(user_id=current_user.get_id() if current_user.is_authenticated else None,
                                  lesson_id=lesson_id, locale=locale, comment=comment, rating=rating)
        db.session.add(fb)
        db.session.commit()
        flash("Thanks for the feedback!", "success")
        return redirect(url_for('lesson', lesson_id=lesson_id))
    return render_template('feedback.html', lesson=lesson)

@app.route('/analytics')
@admin_required
def analytics():
    total_users = db.session.query(func.count(User.id)).scalar()
    total_enrollments = db.session.query(func.count(Enrollment.id)).scalar()
    total_events = db.session.query(func.count(Event.id)).scalar()
    views_per_lesson = db.session.query(Event.lesson_id, func.count(Event.id))\
                        .filter(Event.event_type=='view_lesson')\
                        .group_by(Event.lesson_id)\
                        .order_by(func.count(Event.id).desc())\
                        .limit(10).all()
    recent_feedback = LocalizationFeedback.query.order_by(LocalizationFeedback.created_at.desc()).limit(10).all()
    top = [{'lesson_id': l, 'views': v} for (l,v) in views_per_lesson]
    return render_template('analytics.html',
                           total_users=total_users,
                           total_enrollments=total_enrollments,
                           total_events=total_events,
                           top=top,
                           recent_feedback=recent_feedback)

# ---- AI Assistant ----
@app.route('/assistant', methods=['GET','POST'])
@login_required
def assistant():
    reply = None
    if request.method == 'POST':
        user_input = request.form.get('message')
        # Temporary echo reply; later replace with real AI
        reply = f"You said: {user_input}"
    return render_template('assistant.html', response=reply)
# ---- Authentication ----

@app.route('/signup', methods=['GET', 'POST'])
def signup_view():
    if request.method == 'POST':
        email = request.form.get('email')
        password = bcrypt.generate_password_hash(request.form.get('password')).decode('utf-8')
        if User.query.filter_by(email=email).first():
            flash("Email already exists!", "warning")
            return redirect(url_for('signup_view'))
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for('login_view'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login_view():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for('dashboard_view'))
        else:
            flash("Invalid credentials.", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout_view():
    logout_user()
    flash("You’ve been logged out.", "info")
    return redirect(url_for('index'))

# ---- Dashboard ----
@app.route('/dashboard')
@login_required
def dashboard_view():
    user_enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    completed = sum(1 for e in user_enrollments if e.completed)
    return render_template(
        'dashboard.html',
        user=current_user,
        total=len(user_enrollments),
        completed=completed
    )


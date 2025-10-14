from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# ========================
# App Config
# ========================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'  # replace with strong secret
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///linguabridge.db'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ========================
# User Model
# ========================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self):
        return f"<User {self.email}>"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ========================
# Lessons Data
# ========================
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
        "quiz": [{"question": f"Key concept of Module {i}?","answer": f"Answer {i}"}]
    })

def get_lesson_by_id(lesson_id):
    return next((l for l in lessons if l['id'] == lesson_id), None)

# ========================
# Routes
# ========================

@app.route('/')
def index():
    return render_template('index.html', lessons=lessons)

@app.route('/lesson/<int:lesson_id>')
def lesson(lesson_id):
    lesson = get_lesson_by_id(lesson_id)
    if not lesson:
        abort(404, description="Lesson not found")
    return jsonify(lesson)

# -------- Signup --------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('signup'))
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(email=email, password=hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

# -------- Login --------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check email and password', 'danger')
    return render_template('login.html')

# -------- Logout --------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have logged out.', 'info')
    return redirect(url_for('index'))

# -------- Dashboard --------
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user, lessons=lessons)

# ========================
# Initialize DB
# ========================
with app.app_context():
    db.create_all()

# ========================
# Run App
# ========================
if __name__ == '__main__':
    app.run(debug=False)

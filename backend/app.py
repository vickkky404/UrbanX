from datetime import datetime
# importing flask  module  and calling a perticular flask file
from flask import Flask, render_template, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os
import re
import time
from functools import wraps

# creates the instance for the flask  class
# Configured to serve templates and static files (css/images) from the frontEnd directory
app = Flask(__name__, template_folder='../frontEnd', static_folder='../frontEnd', static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urbanx.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('URBANX_SECRET_KEY', os.urandom(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('URBANX_SECURE_COOKIES', '0') == '1'
db = SQLAlchemy(app)

# Security constants
RATE_LIMIT_STORE = {}
RATE_LIMIT_WINDOW_SECONDS = 600
RATE_LIMIT_MAX_ATTEMPTS = 8
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Captain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=True)
    age = db.Column(db.Integer, nullable=True)  # New field for captain's age
    total_earnings = db.Column(db.Float, default=0.0)  # New field for captain's total earnings

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    balance = db.Column(db.Float, default=1000.0)  # Default sign-up bonus

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pickup = db.Column(db.String(255), nullable=False)
    dropoff = db.Column(db.String(255), nullable=False)
    vehicle_type = db.Column(db.String(50), default='Cab', nullable=False)
    status = db.Column(db.String(50), default='requested', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    captain_id = db.Column(db.Integer, db.ForeignKey('captain.id'), nullable=True)


def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    return response


app.after_request(add_security_headers)


def normalize_email(value: str) -> str:
    return (value or '').strip().lower()


def is_valid_email(value: str) -> bool:
    return bool(EMAIL_PATTERN.match(value or ''))


def validate_password(value: str) -> str:
    if not value or len(value) < 8:
        return 'Password must be at least 8 characters long.'
    if not any(char.isdigit() for char in value):
        return 'Password must include at least one number.'
    return ''


def get_client_ip() -> str:
    forwarded_for = request.headers.get('X-Forwarded-For', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.remote_addr or 'unknown'


def is_rate_limited(key: str) -> bool:
    now = int(time.time())
    attempts = RATE_LIMIT_STORE.get(key, [])
    attempts = [ts for ts in attempts if now - ts < RATE_LIMIT_WINDOW_SECONDS]
    if len(attempts) >= RATE_LIMIT_MAX_ATTEMPTS:
        RATE_LIMIT_STORE[key] = attempts
        return True
    attempts.append(now)
    RATE_LIMIT_STORE[key] = attempts
    return False


def set_auth_session(role: str, subject_id: int):
    session.clear()
    session['role'] = role
    session['subject_id'] = subject_id
    session['issued_at'] = int(time.time())


def login_required(role: str | None = None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not session.get('role'):
                return jsonify({'status': 'error', 'message': 'Authentication required'}), 401
            if role and session.get('role') != role:
                return jsonify({'status': 'error', 'message': 'Insufficient permissions'}), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator


def ensure_user_access(user_id: int):
    return session.get('role') == 'user' and session.get('subject_id') == user_id


def ensure_default_admin():
    admin_email = normalize_email(os.environ.get('URBANX_ADMIN_EMAIL', 'admin@urbanx.com'))
    default_password = os.environ.get('URBANX_ADMIN_PASSWORD')
    if not Admin.query.filter_by(email=admin_email).first():
        admin = Admin(email=admin_email)
        if default_password:
            admin.set_password(default_password)
        else:
            admin.set_password('admin123')
            print('Warning: URBANX_ADMIN_PASSWORD not set; using default admin123')
        db.session.add(admin)
        db.session.commit()


with app.app_context():
    db.create_all()
    ensure_default_admin()

# The route() decorator tells Flask what URL should trigger the function....
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/index.html')
def index_redirect():
    return render_template('index.html')

@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/exploreOurServices.html')
def services():
    return render_template('exploreOurServices.html')

@app.route('/contact.html', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # logic to handle contact form submission
        return render_template('contact.html') # Or redirect to a thank you page
    return render_template('contact.html')

@app.route('/app.html')
def urban_app():
    return render_template('app.html')

@app.route('/captain_dashboard.html')
def captain_dashboard():
    return render_template('captain_dashboard.html')

# Auth Pages Routes
@app.route('/Login/AdminLogin.html')
def admin_login_page():
    return render_template('Login/AdminLogin.html')

@app.route('/Login/CaptainLogin.html')
def captain_login_page():
    return render_template('Login/CaptainLogin.html')

@app.route('/Login/CaptainSignup.html')
def captain_signup_page():
    return render_template('Login/CaptainSignup.html')

@app.route('/Login/UserLogin.html')
def user_login_page():
    # Assuming UserLogin.html exists or will exist in the same structure
    try:
        return render_template('Login/UserLogin.html')
    except:
        return "User Login Page Under Construction", 404

@app.route('/Login/UserSignup.html')
def user_signup_page():
    return render_template('Login/UserSignup.html')

# Route handlers for login/signup API logic
@app.route('/user/signup', methods=['POST'])
def user_signup():
    data = request.get_json(silent=True) or request.form
    fullname = (data.get('fullname') or '').strip()
    email = normalize_email(data.get('email'))
    password = (data.get('password') or '').strip()

    if not fullname or not email or not password:
        return jsonify({"status": "error", "message": "Full name, email, and password are required"}), 400

    if not is_valid_email(email):
        return jsonify({"status": "error", "message": "Enter a valid email address"}), 400

    password_error = validate_password(password)
    if password_error:
        return jsonify({"status": "error", "message": password_error}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already registered"}), 400

    user = User(fullname=fullname, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"status": "ok", "message": "User registered successfully"}), 201

@app.route('/user/login', methods=['POST'])
def user_login():
    data = request.get_json(silent=True) or request.form
    username_or_email = normalize_email(data.get('username'))
    password = (data.get('password') or '').strip()

    if not username_or_email or not password:
        return jsonify({"status": "error", "message": "Email and password are required"}), 400

    if is_rate_limited(f"user_login:{get_client_ip()}"):
        return jsonify({"status": "error", "message": "Too many attempts. Please try again later."}), 429

    user = User.query.filter_by(email=username_or_email).first()

    if user and user.check_password(password):
        set_auth_session('user', user.id)
        return jsonify({"status": "ok", "message": "User authenticated", "user_id": user.id, "fullname": user.fullname}), 200

    return jsonify({"status": "error", "message": "Invalid credentials"}), 401


@app.route('/captain/login', methods=['POST'])
def captain_login():
    data = request.get_json(silent=True) or request.form
    email = normalize_email(data.get('email'))
    password = (data.get('password') or '').strip()
    vehicle_type = (data.get('vehicle_type') or '').strip()

    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required"}), 400

    if is_rate_limited(f"captain_login:{get_client_ip()}"):
        return jsonify({"status": "error", "message": "Too many attempts. Please try again later."}), 429

    captain = Captain.query.filter_by(email=email).first()

    if captain and captain.check_password(password):
        # Verify vehicle type if provided
        if vehicle_type and captain.vehicle_type and vehicle_type.lower() != captain.vehicle_type.lower():
             return jsonify({"status": "error", "message": f"Invalid vehicle type. You are registered as a {captain.vehicle_type} captain."}), 401

        set_auth_session('captain', captain.id)
        return jsonify({
            "status": "ok",
            "message": "Captain authenticated",
            "captain": {
                "id": captain.id,
                "name": captain.name,
                "age": captain.age,
                "vehicle_type": captain.vehicle_type,
                "email": captain.email,
                "total_earnings": captain.total_earnings
            }
        }), 200
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route('/captain/signup', methods=['POST'])
def captain_signup():
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or data.get('fullname') or '').strip()
    email = normalize_email(data.get('email'))
    password = (data.get('password') or '').strip()
    vehicle_type = (data.get('vehicle_type') or '').strip()
    age = data.get('age')

    if not name or not email or not password:
        return jsonify({"status": "error", "message": "Name, email, and password are required"}), 400
    if not is_valid_email(email):
        return jsonify({"status": "error", "message": "Enter a valid email address"}), 400

    password_error = validate_password(password)
    if password_error:
        return jsonify({"status": "error", "message": password_error}), 400

    if age is not None:
        try:
            age = int(age)
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "Age must be a number"}), 400
        if age < 18 or age > 80:
            return jsonify({"status": "error", "message": "Age must be between 18 and 80"}), 400

    if Captain.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already registered"}), 400

    captain = Captain(name=name, email=email, vehicle_type=vehicle_type, age=age)
    captain.set_password(password)
    db.session.add(captain)
    db.session.commit()
    return jsonify({"status": "ok", "message": "Captain registered"}), 201

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or request.form
    email = normalize_email(data.get('email'))
    password = (data.get('password') or '').strip()
    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required"}), 400

    if is_rate_limited(f"admin_login:{get_client_ip()}"):
        return jsonify({"status": "error", "message": "Too many attempts. Please try again later."}), 429

    admin = Admin.query.filter_by(email=email).first()
    if admin and admin.check_password(password):
        set_auth_session('admin', admin.id)
        return jsonify({"status": "ok", "message": "Admin authenticated"}), 200
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route('/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "ok", "message": "Logged out"}), 200

@app.route('/rides', methods=['GET'])
@login_required('user')
def list_rides():
    rides = Ride.query.order_by(Ride.created_at.desc()).all()
    return jsonify({
        "status": "ok",
        "rides": [
            {
                "id": r.id,
                "pickup": r.pickup,
                "dropoff": r.dropoff,
                "vehicle_type": r.vehicle_type,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
                "user_id": r.user_id,
                "captain_id": r.captain_id
            } for r in rides
        ]
    }), 200

@app.route('/rides', methods=['POST'])
@login_required('user')
def create_ride():
    data = request.get_json(silent=True) or request.form
    pickup = data.get('pickup')
    dropoff = data.get('dropoff')
    vehicle_type = data.get('vehicle_type') or 'Cab'
    user_id = session.get('subject_id')

    if not pickup or not dropoff:
        return jsonify({"status": "error", "message": "pickup and dropoff are required"}), 400

    ride = Ride(pickup=pickup, dropoff=dropoff, vehicle_type=vehicle_type, user_id=user_id)
    db.session.add(ride)
    db.session.commit()
    return jsonify({"status": "ok", "ride_id": ride.id, "message": "Ride created"}), 201

@app.route('/api/user/<int:user_id>/wallet', methods=['GET', 'POST'])
def user_wallet(user_id):
    if not ensure_user_access(user_id):
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        amount = float(data.get('amount', 0))
        if amount > 0:
            user.balance += amount
            db.session.commit()
            return jsonify({"status": "ok", "message": "Funds added", "balance": user.balance})
        return jsonify({"status": "error", "message": "Invalid amount"}), 400

    return jsonify({"status": "ok", "balance": user.balance, "currency": "₹"})

@app.route('/api/user/<int:user_id>/profile', methods=['POST'])
def update_profile(user_id):
    if not ensure_user_access(user_id):
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    data = request.get_json(silent=True) or request.form
    fullname = data.get('fullname')
    email = normalize_email(data.get('email'))

    if fullname:
        user.fullname = fullname
    if email:
        if not is_valid_email(email):
            return jsonify({"status": "error", "message": "Enter a valid email address"}), 400
        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != user.id:
            return jsonify({"status": "error", "message": "Email already in use"}), 400
        user.email = email

    db.session.commit()
    return jsonify({"status": "ok", "message": "Profile updated", "user": {"id": user.id, "fullname": user.fullname, "email": user.email}}), 200

# Endpoint to get fare estimates for different vehicle types
@app.route('/api/fare/estimate', methods=['POST'])
def estimate_fare():
    data = request.get_json(silent=True) or request.form
    # In a real app, distance would be calculated from pickup/dropoff coords
    # Here we accept an estimated distance or default to 5km
    distance_km = float(data.get('distance_km', 5.0))

    # Pricing configuration (per km)
    rates = {
        'Cab': 21.0,
        'Auto': 10.0,
        'Moto': 7.0,
        'Cycle': 2.0  # Set to 8 Rupees as per request
    }

    estimates = {}
    for v_type, rate in rates.items():
        estimates[v_type] = round(rate * distance_km, 2)

    return jsonify({
        "status": "ok",
        "estimates": estimates,
        "currency": "₹",
        "distance_km": distance_km
    })

#  ///////////////////
# runs the applicaiton
# defualt port for flask is 5000
if __name__ == "__main__":
    app.run(debug=True)

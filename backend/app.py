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
    phone = db.Column(db.String(20), nullable=True)
    vehicle_type = db.Column(db.String(50), nullable=True)
    vehicle_number = db.Column(db.String(50), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    gender = db.Column(db.String(20), nullable=True)  # male, female, other
    total_earnings = db.Column(db.Float, default=0.0)
    is_verified = db.Column(db.Boolean, default=False)
    is_online = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    phone = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(20), nullable=True)  # male, female, other
    balance = db.Column(db.Float, default=1000.0)  # Default sign-up bonus
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pickup = db.Column(db.String(255), nullable=False)
    dropoff = db.Column(db.String(255), nullable=False)
    pickup_lat = db.Column(db.Float, nullable=True)
    pickup_lon = db.Column(db.Float, nullable=True)
    dropoff_lat = db.Column(db.Float, nullable=True)
    dropoff_lon = db.Column(db.Float, nullable=True)
    vehicle_type = db.Column(db.String(50), default='Cab', nullable=False)
    status = db.Column(db.String(50), default='requested', nullable=False)
    fare = db.Column(db.Float, default=0.0)
    distance_km = db.Column(db.Float, default=0.0)
    scheduled_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    captain_id = db.Column(db.Integer, db.ForeignKey('captain.id'), nullable=True)
    promo_code = db.Column(db.String(50), nullable=True)
    discount = db.Column(db.Float, default=0.0)


class SavedPlace(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    place_type = db.Column(db.String(50), default='custom')  # home, work, custom
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)  # credit, debit
    description = db.Column(db.String(255), nullable=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class PromoCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_percent = db.Column(db.Float, default=0)
    discount_amount = db.Column(db.Float, default=0)
    max_discount = db.Column(db.Float, default=100)
    min_ride_amount = db.Column(db.Float, default=0)
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=True)
    usage_limit = db.Column(db.Integer, default=1)
    times_used = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)


class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ride_id = db.Column(db.Integer, db.ForeignKey('ride.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    captain_id = db.Column(db.Integer, db.ForeignKey('captain.id'), nullable=True)
    stars = db.Column(db.Integer, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    tip_amount = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50), default='info')  # info, promo, ride, alert
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


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
    gender = (data.get('gender') or '').strip().lower()

    if not fullname or not email or not password:
        return jsonify({"status": "error", "message": "Full name, email, and password are required"}), 400

    if not is_valid_email(email):
        return jsonify({"status": "error", "message": "Enter a valid email address"}), 400

    if gender and gender not in ['male', 'female', 'other']:
        return jsonify({"status": "error", "message": "Invalid gender selection"}), 400

    password_error = validate_password(password)
    if password_error:
        return jsonify({"status": "error", "message": password_error}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already registered"}), 400

    user = User(fullname=fullname, email=email, gender=gender if gender else None)
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
                "gender": captain.gender,
                "phone": captain.phone,
                "vehicle_type": captain.vehicle_type,
                "vehicle_number": captain.vehicle_number,
                "email": captain.email,
                "total_earnings": captain.total_earnings,
                "is_verified": captain.is_verified
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
    vehicle_number = (data.get('vehicle_number') or '').strip()
    phone = (data.get('phone') or '').strip()
    gender = (data.get('gender') or '').strip().lower()
    age = data.get('age')

    if not name or not email or not password:
        return jsonify({"status": "error", "message": "Name, email, and password are required"}), 400
    if not is_valid_email(email):
        return jsonify({"status": "error", "message": "Enter a valid email address"}), 400
    if not gender or gender not in ['male', 'female', 'other']:
        return jsonify({"status": "error", "message": "Please select your gender"}), 400

    password_error = validate_password(password)
    if password_error:
        return jsonify({"status": "error", "message": password_error}), 400

    if age is not None:
        try:
            age = int(age)
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "Age must be a number"}), 400
        # Allow teens (16+) for cycle, 18+ for bike/auto, 21+ for cab
        if age < 16 or age > 80:
            return jsonify({"status": "error", "message": "Age must be between 16 and 80"}), 400

        # Validate age requirements for vehicle type
        if vehicle_type == 'Cab' and age < 21:
            return jsonify({"status": "error", "message": "You must be 21+ to drive a Cab"}), 400
        if vehicle_type in ['Bike', 'Auto'] and age < 18:
            return jsonify({"status": "error", "message": "You must be 18+ to drive a Bike or Auto"}), 400
        if vehicle_type == 'Cycle' and age < 16:
            return jsonify({"status": "error", "message": "You must be 16+ to use a Cycle"}), 400

    if Captain.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already registered"}), 400

    # Set is_verified to False for young captains requiring document verification
    is_verified = True if age and age > 21 else False

    captain = Captain(
        name=name,
        email=email,
        vehicle_type=vehicle_type,
        vehicle_number=vehicle_number,
        phone=phone,
        gender=gender,
        age=age,
        is_verified=is_verified
    )
    captain.set_password(password)
    db.session.add(captain)
    db.session.commit()

    message = "Captain registered successfully!"
    if not is_verified:
        message += " Your documents will be verified within 24-48 hours."

    return jsonify({"status": "ok", "message": message, "captain_id": captain.id}), 201

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

# Old rides routes removed - using enhanced versions below

@app.route('/rides', methods=['GET'])
def list_all_rides():
    rides = Ride.query.order_by(Ride.created_at.desc()).limit(100).all()
    return jsonify({
        "status": "ok",
        "rides": [{
            "id": r.id,
            "pickup": r.pickup,
            "dropoff": r.dropoff,
            "vehicle_type": r.vehicle_type,
            "status": r.status,
            "fare": r.fare,
            "distance_km": r.distance_km,
            "user_id": r.user_id,
            "created_at": r.created_at.isoformat()
        } for r in rides]
    })

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
        'Cycle': 8.0
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


@app.route('/api/geocode', methods=['GET'])
def geocode():
    # Simple proxy to OpenStreetMap Nominatim API
    # In a production app, you should use a proper geocoding service key (Google Maps, Mapbox, etc.)
    q = request.args.get('q')
    lat = request.args.get('lat')
    lon = request.args.get('lon')

    headers = {'User-Agent': 'UrbanX/1.0 (urbanx@example.com)'}

    try:
        if lat and lon:
            # Reverse Geocode
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return jsonify(data)
        elif q:
            # Forward Geocode
            url = f"https://nominatim.openstreetmap.org/search?format=json&q={requests.utils.quote(q)}"
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return jsonify(data)
    except Exception as e:
        print(f"Geocoding error: {e}")
        return jsonify({"error": "Geocoding service unavailable"}), 503

    return jsonify({})


# ========================================
# SAVED PLACES API
# ========================================
@app.route('/api/user/<int:user_id>/places', methods=['GET'])
def get_saved_places(user_id):
    if not ensure_user_access(user_id):
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    places = SavedPlace.query.filter_by(user_id=user_id).order_by(SavedPlace.created_at.desc()).all()
    return jsonify({
        "status": "ok",
        "places": [{
            "id": p.id,
            "name": p.name,
            "address": p.address,
            "place_type": p.place_type,
            "lat": p.lat,
            "lon": p.lon
        } for p in places]
    })


@app.route('/api/user/<int:user_id>/places', methods=['POST'])
def add_saved_place(user_id):
    if not ensure_user_access(user_id):
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    data = request.get_json(silent=True) or request.form
    name = data.get('name', '').strip()
    address = data.get('address', '').strip()
    place_type = data.get('place_type', 'custom')
    lat = data.get('lat')
    lon = data.get('lon')

    if not name or not address:
        return jsonify({"status": "error", "message": "Name and address required"}), 400

    # Check if home/work already exists
    if place_type in ['home', 'work']:
        existing = SavedPlace.query.filter_by(user_id=user_id, place_type=place_type).first()
        if existing:
            existing.name = name
            existing.address = address
            existing.lat = lat
            existing.lon = lon
            db.session.commit()
            return jsonify({"status": "ok", "message": f"{place_type.title()} updated", "place_id": existing.id})

    place = SavedPlace(user_id=user_id, name=name, address=address, place_type=place_type, lat=lat, lon=lon)
    db.session.add(place)
    db.session.commit()
    return jsonify({"status": "ok", "message": "Place saved", "place_id": place.id}), 201


@app.route('/api/user/<int:user_id>/places/<int:place_id>', methods=['DELETE'])
def delete_saved_place(user_id, place_id):
    if not ensure_user_access(user_id):
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    place = SavedPlace.query.filter_by(id=place_id, user_id=user_id).first()
    if not place:
        return jsonify({"status": "error", "message": "Place not found"}), 404

    db.session.delete(place)
    db.session.commit()
    return jsonify({"status": "ok", "message": "Place deleted"})


# ========================================
# TRANSACTIONS API
# ========================================
@app.route('/api/user/<int:user_id>/transactions', methods=['GET'])
def get_transactions(user_id):
    if not ensure_user_access(user_id):
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.created_at.desc()).limit(50).all()
    return jsonify({
        "status": "ok",
        "transactions": [{
            "id": t.id,
            "amount": t.amount,
            "type": t.transaction_type,
            "description": t.description,
            "ride_id": t.ride_id,
            "created_at": t.created_at.isoformat()
        } for t in transactions]
    })


# ========================================
# PROMO CODE API
# ========================================
@app.route('/api/promo/validate', methods=['POST'])
def validate_promo():
    data = request.get_json(silent=True) or request.form
    code = (data.get('code') or '').strip().upper()
    ride_amount = float(data.get('ride_amount', 0))

    if not code:
        return jsonify({"status": "error", "message": "Promo code required"}), 400

    promo = PromoCode.query.filter_by(code=code, is_active=True).first()

    if not promo:
        return jsonify({"status": "error", "message": "Invalid promo code"}), 404

    now = datetime.utcnow()
    if promo.valid_until and promo.valid_until < now:
        return jsonify({"status": "error", "message": "Promo code expired"}), 400

    if promo.times_used >= promo.usage_limit:
        return jsonify({"status": "error", "message": "Promo code usage limit reached"}), 400

    if ride_amount < promo.min_ride_amount:
        return jsonify({"status": "error", "message": f"Minimum ride amount ₹{promo.min_ride_amount} required"}), 400

    # Calculate discount
    discount = 0
    if promo.discount_percent > 0:
        discount = ride_amount * (promo.discount_percent / 100)
    if promo.discount_amount > 0:
        discount = promo.discount_amount

    discount = min(discount, promo.max_discount)

    return jsonify({
        "status": "ok",
        "code": promo.code,
        "discount": round(discount, 2),
        "message": f"₹{round(discount, 2)} discount applied!"
    })


@app.route('/api/promo/list', methods=['GET'])
def list_promos():
    now = datetime.utcnow()
    promos = PromoCode.query.filter(
        PromoCode.is_active == True,
        (PromoCode.valid_until == None) | (PromoCode.valid_until > now)
    ).all()

    return jsonify({
        "status": "ok",
        "promos": [{
            "code": p.code,
            "discount_percent": p.discount_percent,
            "discount_amount": p.discount_amount,
            "max_discount": p.max_discount,
            "min_ride_amount": p.min_ride_amount,
            "valid_until": p.valid_until.isoformat() if p.valid_until else None
        } for p in promos]
    })


# ========================================
# RATING API
# ========================================
@app.route('/api/rides/<int:ride_id>/rating', methods=['POST'])
def submit_rating(ride_id):
    data = request.get_json(silent=True) or request.form
    stars = int(data.get('stars', 0))
    feedback = data.get('feedback', '').strip()
    tip_amount = float(data.get('tip', 0))

    if stars < 1 or stars > 5:
        return jsonify({"status": "error", "message": "Rating must be 1-5 stars"}), 400

    ride = Ride.query.get(ride_id)
    if not ride:
        return jsonify({"status": "error", "message": "Ride not found"}), 404

    # Check if already rated
    existing = Rating.query.filter_by(ride_id=ride_id).first()
    if existing:
        return jsonify({"status": "error", "message": "Ride already rated"}), 400

    rating = Rating(
        ride_id=ride_id,
        user_id=ride.user_id,
        captain_id=ride.captain_id,
        stars=stars,
        feedback=feedback,
        tip_amount=tip_amount
    )
    db.session.add(rating)

    # Process tip if any
    if tip_amount > 0 and ride.user_id:
        user = User.query.get(ride.user_id)
        if user and user.balance >= tip_amount:
            user.balance -= tip_amount
            # Add transaction
            tx = Transaction(
                user_id=ride.user_id,
                amount=-tip_amount,
                transaction_type='debit',
                description=f'Tip for ride #{ride_id}',
                ride_id=ride_id
            )
            db.session.add(tx)

    db.session.commit()
    return jsonify({"status": "ok", "message": "Thank you for your feedback!"})


# ========================================
# NOTIFICATIONS API
# ========================================
@app.route('/api/user/<int:user_id>/notifications', methods=['GET'])
def get_notifications(user_id):
    if not ensure_user_access(user_id):
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(20).all()
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()

    return jsonify({
        "status": "ok",
        "unread_count": unread_count,
        "notifications": [{
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.notification_type,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat()
        } for n in notifications]
    })


@app.route('/api/user/<int:user_id>/notifications/read', methods=['POST'])
def mark_notifications_read(user_id):
    if not ensure_user_access(user_id):
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({"status": "ok", "message": "Notifications marked as read"})


# ========================================
# USER STATS API
# ========================================
@app.route('/api/user/<int:user_id>/stats', methods=['GET'])
def get_user_stats(user_id):
    if not ensure_user_access(user_id):
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404

    total_rides = Ride.query.filter_by(user_id=user_id).count()
    completed_rides = Ride.query.filter_by(user_id=user_id, status='completed').count()
    total_spent = db.session.query(db.func.sum(Ride.fare)).filter_by(user_id=user_id, status='completed').scalar() or 0
    total_distance = db.session.query(db.func.sum(Ride.distance_km)).filter_by(user_id=user_id, status='completed').scalar() or 0

    # Get favorite vehicle type
    from sqlalchemy import func
    fav_vehicle = db.session.query(Ride.vehicle_type, func.count(Ride.id).label('count'))\
        .filter_by(user_id=user_id)\
        .group_by(Ride.vehicle_type)\
        .order_by(func.count(Ride.id).desc())\
        .first()

    return jsonify({
        "status": "ok",
        "stats": {
            "total_rides": total_rides,
            "completed_rides": completed_rides,
            "total_spent": round(total_spent, 2),
            "total_distance_km": round(total_distance, 2),
            "balance": user.balance,
            "favorite_vehicle": fav_vehicle[0] if fav_vehicle else None,
            "member_since": user.id  # Could add created_at to User model
        }
    })


# ========================================
# ENHANCED RIDE API
# ========================================
@app.route('/rides', methods=['POST'])
@login_required('user')
def create_ride():
    data = request.get_json(silent=True) or request.form
    pickup = data.get('pickup')
    dropoff = data.get('dropoff')
    vehicle_type = data.get('vehicle_type') or 'Cab'
    user_id = session.get('subject_id')
    pickup_lat = data.get('pickup_lat')
    pickup_lon = data.get('pickup_lon')
    dropoff_lat = data.get('dropoff_lat')
    dropoff_lon = data.get('dropoff_lon')
    distance_km = float(data.get('distance_km', 0))
    fare = float(data.get('fare', 0))
    scheduled_at = data.get('scheduled_at')
    promo_code = data.get('promo_code')

    if not pickup or not dropoff:
        return jsonify({"status": "error", "message": "pickup and dropoff are required"}), 400

    # Validate promo code if provided
    discount = 0
    if promo_code:
        promo = PromoCode.query.filter_by(code=promo_code.upper(), is_active=True).first()
        if promo and fare >= promo.min_ride_amount:
            if promo.discount_percent > 0:
                discount = fare * (promo.discount_percent / 100)
            elif promo.discount_amount > 0:
                discount = promo.discount_amount
            discount = min(discount, promo.max_discount)
            promo.times_used += 1

    final_fare = max(0, fare - discount)

    ride = Ride(
        pickup=pickup,
        dropoff=dropoff,
        pickup_lat=pickup_lat,
        pickup_lon=pickup_lon,
        dropoff_lat=dropoff_lat,
        dropoff_lon=dropoff_lon,
        vehicle_type=vehicle_type,
        user_id=user_id,
        distance_km=distance_km,
        fare=final_fare,
        promo_code=promo_code,
        discount=discount,
        scheduled_at=datetime.fromisoformat(scheduled_at) if scheduled_at else None
    )
    db.session.add(ride)

    # Deduct from wallet
    user = User.query.get(user_id)
    if user and user.balance >= final_fare:
        user.balance -= final_fare
        tx = Transaction(
            user_id=user_id,
            amount=-final_fare,
            transaction_type='debit',
            description=f'Ride #{ride.id} - {vehicle_type}',
            ride_id=ride.id
        )
        db.session.add(tx)

    db.session.commit()
    return jsonify({
        "status": "ok",
        "ride_id": ride.id,
        "fare": final_fare,
        "discount": discount,
        "message": "Ride created"
    }), 201


@app.route('/rides/<int:ride_id>/cancel', methods=['POST'])
def cancel_ride(ride_id):
    ride = Ride.query.get(ride_id)
    if not ride:
        return jsonify({"status": "error", "message": "Ride not found"}), 404

    if ride.status not in ['requested', 'accepted']:
        return jsonify({"status": "error", "message": "Ride cannot be cancelled"}), 400

    ride.status = 'cancelled'

    # Refund to wallet (partial if captain accepted)
    if ride.user_id and ride.fare > 0:
        user = User.query.get(ride.user_id)
        refund = ride.fare if ride.status == 'requested' else ride.fare * 0.8  # 20% cancellation fee
        if user:
            user.balance += refund
            tx = Transaction(
                user_id=ride.user_id,
                amount=refund,
                transaction_type='credit',
                description=f'Refund for cancelled ride #{ride_id}',
                ride_id=ride_id
            )
            db.session.add(tx)

    db.session.commit()
    return jsonify({"status": "ok", "message": "Ride cancelled"})


@app.route('/api/user/<int:user_id>/rides', methods=['GET'])
def get_user_rides(user_id):
    if not ensure_user_access(user_id):
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    rides = Ride.query.filter_by(user_id=user_id).order_by(Ride.created_at.desc()).limit(50).all()
    return jsonify({
        "status": "ok",
        "rides": [{
            "id": r.id,
            "pickup": r.pickup,
            "dropoff": r.dropoff,
            "vehicle_type": r.vehicle_type,
            "status": r.status,
            "fare": r.fare,
            "distance_km": r.distance_km,
            "discount": r.discount,
            "created_at": r.created_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None
        } for r in rides]
    })


# Initialize default promo codes
def ensure_default_promos():
    promos = [
        {'code': 'URBAN50', 'discount_percent': 50, 'max_discount': 100, 'usage_limit': 100},
        {'code': 'WEEKEND20', 'discount_percent': 20, 'max_discount': 50, 'usage_limit': 500},
        {'code': 'MOTO30', 'discount_amount': 30, 'max_discount': 30, 'usage_limit': 200},
        {'code': 'NEWUSER', 'discount_percent': 40, 'max_discount': 80, 'usage_limit': 1000},
    ]
    for p in promos:
        if not PromoCode.query.filter_by(code=p['code']).first():
            promo = PromoCode(**p)
            db.session.add(promo)
    db.session.commit()


# ========================================
# CAPTAIN API ENDPOINTS
# ========================================

@app.route('/api/captain/rides/pending', methods=['GET'])
def get_pending_rides():
    vehicle_type = request.args.get('vehicle_type', 'Cab')
    captain_gender = request.args.get('gender')

    # Base query for pending rides
    query = Ride.query.filter_by(status='requested', vehicle_type=vehicle_type)

    # If captain gender is provided, filter rides by matching user gender
    if captain_gender and captain_gender in ['male', 'female']:
        # Get user IDs that match the captain's gender
        matching_users = User.query.filter_by(gender=captain_gender).with_entities(User.id).all()
        matching_user_ids = [u.id for u in matching_users]

        # Also include rides where user gender is not specified (for backward compatibility)
        query = query.filter(
            db.or_(
                Ride.user_id.in_(matching_user_ids),
                Ride.user_id.is_(None)
            )
        )

    rides = query.order_by(Ride.created_at.desc()).limit(10).all()

    return jsonify({
        "status": "ok",
        "rides": [{
            "id": r.id,
            "pickup": r.pickup,
            "dropoff": r.dropoff,
            "vehicle_type": r.vehicle_type,
            "fare": r.fare,
            "distance_km": r.distance_km,
            "created_at": r.created_at.isoformat()
        } for r in rides]
    })


@app.route('/api/captain/rides/<int:ride_id>/accept', methods=['POST'])
def captain_accept_ride(ride_id):
    data = request.get_json(silent=True) or request.form
    captain_id = data.get('captain_id')

    ride = Ride.query.get(ride_id)
    if not ride:
        return jsonify({"status": "error", "message": "Ride not found"}), 404

    if ride.status != 'requested':
        return jsonify({"status": "error", "message": "Ride already taken"}), 400

    ride.status = 'accepted'
    ride.captain_id = captain_id
    db.session.commit()

    return jsonify({"status": "ok", "message": "Ride accepted"})


@app.route('/api/captain/rides/<int:ride_id>/complete', methods=['POST'])
def captain_complete_ride(ride_id):
    data = request.get_json(silent=True) or request.form
    captain_id = data.get('captain_id')

    ride = Ride.query.get(ride_id)
    if not ride:
        return jsonify({"status": "error", "message": "Ride not found"}), 404

    ride.status = 'completed'
    ride.completed_at = datetime.utcnow()

    # Add earnings to captain
    if captain_id:
        captain = Captain.query.get(captain_id)
        if captain:
            captain.total_earnings = (captain.total_earnings or 0) + (ride.fare or 0)

    db.session.commit()

    return jsonify({"status": "ok", "message": "Ride completed"})


@app.route('/api/captain/<int:captain_id>/rides', methods=['GET'])
def get_captain_rides(captain_id):
    rides = Ride.query.filter_by(captain_id=captain_id).order_by(Ride.created_at.desc()).limit(50).all()
    return jsonify({
        "status": "ok",
        "rides": [{
            "id": r.id,
            "pickup": r.pickup,
            "dropoff": r.dropoff,
            "vehicle_type": r.vehicle_type,
            "status": r.status,
            "fare": r.fare,
            "distance_km": r.distance_km,
            "created_at": r.created_at.isoformat()
        } for r in rides]
    })


@app.route('/api/captain/<int:captain_id>/stats', methods=['GET'])
def get_captain_stats(captain_id):
    captain = Captain.query.get(captain_id)
    if not captain:
        return jsonify({"status": "error", "message": "Captain not found"}), 404

    from datetime import date
    today = date.today()

    today_rides = Ride.query.filter(
        Ride.captain_id == captain_id,
        Ride.status == 'completed',
        db.func.date(Ride.completed_at) == today
    ).all()

    today_earnings = sum(r.fare or 0 for r in today_rides)

    return jsonify({
        "status": "ok",
        "stats": {
            "today_earnings": today_earnings,
            "trips_today": len(today_rides),
            "total_earnings": captain.total_earnings or 0,
            "rating": 4.8  # Would calculate from Rating table
        }
    })


with app.app_context():
    db.create_all()
    ensure_default_admin()
    ensure_default_promos()


#  ///////////////////
# runs the application
# default port for flask is 5000
if __name__ == "__main__":
    app.run(debug=True)

from datetime import datetime
# importing flask  module  and calling a perticular flask file
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# creates the instance for the flask  class
# Configured to serve templates and static files (css/images) from the frontEnd directory
app = Flask(__name__, template_folder='../frontEnd', static_folder='../frontEnd', static_url_path='')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urbanx.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Captain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

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


class Ride(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pickup = db.Column(db.String(255), nullable=False)
    dropoff = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(50), default='requested', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


def ensure_default_admin():
    if not Admin.query.filter_by(email="admin@urbanx.com").first():
        admin = Admin(email="admin@urbanx.com")
        admin.set_password("admin123")
        db.session.add(admin)
        db.session.commit()


with app.app_context():
    db.create_all()
    ensure_default_admin()

# The route() decorator tells Flask what URL should trigger the function....
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/app.html')
def urban_app():
    return render_template('app.html')

# Route handlers for login/signup forms
@app.route('/captain/login', methods=['POST'])
def captain_login():
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()
    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required"}), 400
    captain = Captain.query.filter_by(email=email).first()
    if captain and captain.check_password(password):
        return jsonify({"status": "ok", "message": "Captain authenticated"}), 200
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route('/captain/signup', methods=['POST'])
def captain_signup():
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()
    if not name or not email or not password:
        return jsonify({"status": "error", "message": "Name, email, and password are required"}), 400
    if Captain.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "Email already registered"}), 400
    captain = Captain(name=name, email=email)
    captain.set_password(password)
    db.session.add(captain)
    db.session.commit()
    return jsonify({"status": "ok", "message": "Captain registered"}), 201

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or request.form
    email = (data.get('email') or '').strip()
    password = (data.get('password') or '').strip()
    if not email or not password:
        return jsonify({"status": "error", "message": "Email and password are required"}), 400
    admin = Admin.query.filter_by(email=email).first()
    if admin and admin.check_password(password):
        return jsonify({"status": "ok", "message": "Admin authenticated"}), 200
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401

@app.route('/rides', methods=['GET'])
def list_rides():
    rides = Ride.query.order_by(Ride.created_at.desc()).all()
    return jsonify({
        "status": "ok",
        "rides": [
            {
                "id": r.id,
                "pickup": r.pickup,
                "dropoff": r.dropoff,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            } for r in rides
        ]
    }), 200

@app.route('/rides', methods=['POST'])
def create_ride():
    data = request.get_json(silent=True) or request.form
    pickup = data.get('pickup')
    dropoff = data.get('dropoff')
    if not pickup or not dropoff:
        return jsonify({"status": "error", "message": "pickup and dropoff are required"}), 400
    ride = Ride(pickup=pickup, dropoff=dropoff)
    db.session.add(ride)
    db.session.commit()
    return jsonify({"status": "ok", "ride_id": ride.id, "message": "Ride created"}), 201

@app.route('/rides/<int:ride_id>', methods=['GET'])
def get_ride(ride_id):
    ride = Ride.query.get(ride_id)
    if not ride:
        return jsonify({"status": "error", "message": "Ride not found"}), 404
    return jsonify({
        "status": "ok",
        "ride": {
            "id": ride.id,
            "pickup": ride.pickup,
            "dropoff": ride.dropoff,
            "status": ride.status,
            "created_at": ride.created_at.isoformat(),
            "updated_at": ride.updated_at.isoformat()
        }
    }), 200

#  ///////////////////
# runs the applicaiton
# defualt port for flask is 5000
if __name__ == "__main__":
    app.run(debug=True)

from app import app, db, User
import sys

try:
    with app.app_context():
        # Try to query the User table
        count = User.query.count()
        print(f"User table exists. Count: {count}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)


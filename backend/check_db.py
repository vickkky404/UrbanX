from app import app, db, User
import sys

try:
    with app.app_context():
        # Try to query the User table
        count = User.query.count()
        print(f"User table exists. Count: {count}")
        users = User.query.all()
        for u in users:
            print(f"User: {u.id}, {u.fullname}, {u.email}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)


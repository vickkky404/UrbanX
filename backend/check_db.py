from app import app, db, User
import sys
import os
import sqlite3

print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
print(f"Instance Path: {app.INSTANCE_FOLDER_PATH if hasattr(app, 'INSTANCE_FOLDER_PATH') else app.instance_path}")
db_file = os.path.join(app.instance_path, 'urbanx.db')
print(f"Expected DB File: {db_file}")
print(f"DB File Exists: {os.path.exists(db_file)}")

c = sqlite3.connect(db_file)
cu = c.cursor()
try:
    print("--- SCHEMA DUMP ---")
    cu.execute("PRAGMA table_info(user)")
    for col in cu.fetchall():
        print(f"User Col: {col}")
    cu.execute("PRAGMA table_info(captain)")
    for col in cu.fetchall():
        print(f"Captain Col: {col}")
    print("-------------------")
except Exception as ex:
    print(f"Schema dump error: {ex}")
c.close()

try:
    with app.app_context():
        count = User.query.count()
        print(f"User table exists. Count: {count}")
        users = User.query.all()
        for u in users:
            print(f"User: {u.id}, {u.fullname}, {u.email}")
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)

import sqlite3
import os

db_path = os.path.join('instance', 'urbanx.db')
if not os.path.exists(db_path):
    print("Database not found, skipping migration.")
    exit()

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    print("Checking for column 'age' in 'captain' table...")
    cursor.execute("SELECT age FROM captain LIMIT 1")
    print("Column 'age' already exists.")
except sqlite3.OperationalError:
    print("Adding column 'age'...")
    try:
        cursor.execute("ALTER TABLE captain ADD COLUMN age INTEGER")
        print("Column 'age' added.")
    except Exception as e:
        print(f"Error adding 'age': {e}")

try:
    print("Checking for column 'total_earnings' in 'captain' table...")
    cursor.execute("SELECT total_earnings FROM captain LIMIT 1")
    print("Column 'total_earnings' already exists.")
except sqlite3.OperationalError:
    print("Adding column 'total_earnings'...")
    try:
        cursor.execute("ALTER TABLE captain ADD COLUMN total_earnings REAL DEFAULT 0.0")
        print("Column 'total_earnings' added.")
    except Exception as e:
        print(f"Error adding 'total_earnings': {e}")

conn.commit()
conn.close()
print("Database schema update complete.")


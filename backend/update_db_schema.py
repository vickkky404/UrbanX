import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'instance', 'urbanx.db')
if not os.path.exists(db_path):
    # try check if running from backend root
    db_path = os.path.join('instance', 'urbanx.db')
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}, skipping migration.")
        exit()

print(f"Updating database at: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def add_column_if_not_exists(table, column, definition):
    try:
        cursor.execute(f"SELECT {column} FROM {table} LIMIT 1")
        print(f"Column '{column}' in table '{table}' already exists.")
    except sqlite3.OperationalError:
        print(f"Adding column '{column}' to table '{table}'...")
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            print(f"Column '{column}' added.")
        except Exception as e:
            print(f"Error adding '{column}': {e}")


add_column_if_not_exists('captain', 'age', 'INTEGER')
add_column_if_not_exists('captain', 'total_earnings', 'REAL DEFAULT 0.0')
add_column_if_not_exists('captain', 'vehicle_type', 'TEXT')
add_column_if_not_exists('captain', 'vehicle_number', 'TEXT')
add_column_if_not_exists('captain', 'phone', 'TEXT')
add_column_if_not_exists('captain', 'gender', 'TEXT')
add_column_if_not_exists('captain', 'is_verified', 'BOOLEAN DEFAULT 0')
add_column_if_not_exists('captain', 'is_online', 'BOOLEAN DEFAULT 0')
add_column_if_not_exists('captain', 'created_at', 'DATETIME')


add_column_if_not_exists('user', 'phone', 'TEXT')
add_column_if_not_exists('user', 'gender', 'TEXT')
add_column_if_not_exists('user', 'balance', 'REAL DEFAULT 1000.0')
add_column_if_not_exists('user', 'created_at', 'DATETIME')

conn.commit()
conn.close()
print("Database schema update complete.")

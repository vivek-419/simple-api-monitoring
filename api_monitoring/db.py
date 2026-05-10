import sqlite3
import os

DB_PATH = 'monitoring.db'

def get_connection():
    """Returns a SQLite connection with dict factory for rows."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create metrics table
    # Storing timestamp as an integer (Unix timestamp) or string (ISO 8601)
    # Using unix timestamp for easier querying/aggregation
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            timestamp REAL NOT NULL,
            value REAL NOT NULL,
            service_id TEXT NOT NULL,
            endpoint TEXT
        )
    ''')

    # Create alerts table (configuration)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_rules (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric_name TEXT NOT NULL,
            threshold REAL NOT NULL,
            condition TEXT NOT NULL,
            notification_type TEXT NOT NULL,
            created_at REAL NOT NULL,
            service_id TEXT
        )
    ''')

    # Create triggered alerts table (history)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS triggered_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id INTEGER,
            metric_name TEXT,
            value REAL,
            threshold REAL,
            condition TEXT,
            timestamp REAL,
            service_id TEXT,
            FOREIGN KEY(alert_id) REFERENCES alert_rules(alert_id)
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized successfully.")

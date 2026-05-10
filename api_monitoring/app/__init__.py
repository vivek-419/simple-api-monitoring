import sqlite3
import time
import os
from flask import Flask, jsonify
from app.routes.metrics import metrics_bp
from app.routes.alerts import alerts_bp
from app.routes.dashboard import dashboard_bp

DB_PATH = 'monitoring.db'
METRIC_RETENTION_HOURS = 24

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_rule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT NOT NULL,
            service_name TEXT,
            metric_type TEXT NOT NULL,
            condition TEXT NOT NULL,
            threshold REAL NOT NULL,
            time_window_minutes INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at REAL NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id INTEGER NOT NULL,
            metric_value REAL NOT NULL,
            message TEXT NOT NULL,
            triggered_at REAL NOT NULL,
            resolved INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (rule_id) REFERENCES alert_rule (id)
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM alert_rule")
    count = cursor.fetchone()[0]
    
    if count == 0:
        default_rules = [
            ("High Error Rate", None, "error_rate", "gt", 5.0, 5),
            ("High Latency", None, "avg_latency", "gt", 500.0, 5),
            ("Low Traffic Warning", None, "rps", "lt", 0.1, 10),
            ("Latency Spike (Z-Score)", None, "avg_latency", "anomaly_zscore", 3.0, 15)
        ]
        
        for r in default_rules:
            cursor.execute('''
                INSERT INTO alert_rule (rule_name, service_name, metric_type, condition, threshold, time_window_minutes, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            ''', (r[0], r[1], r[2], r[3], r[4], r[5], time.time()))
            
    conn.commit()
    conn.close()

def cleanup_old_metrics():
    cutoff = time.time() - (METRIC_RETENTION_HOURS * 3600)
    conn = get_db()
    cursor = conn.cursor()
    # Check if table exists before deleting to avoid errors on fresh start
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metric_entry'")
    if cursor.fetchone():
        cursor.execute("DELETE FROM metric_entry WHERE timestamp < ?", (cutoff,))
        deleted = cursor.rowcount
        conn.commit()
        if deleted > 0:
            print(f"[Cleanup] Deleted {deleted} old metric records.")
    conn.close()

def create_app():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__, 
                template_folder=os.path.join(base_dir, 'templates'),
                static_folder=os.path.join(base_dir, 'static'))
    
    init_db()
    
    app.register_blueprint(metrics_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(dashboard_bp)
    
    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
        return response

    @app.route('/health', methods=['GET'])
    def health_check():
        from datetime import datetime
        return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"})
    
    return app

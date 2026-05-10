import sqlite3
import time
from flask import Blueprint, request, jsonify
from app.services.alert_engine import check_all_alerts

alerts_bp = Blueprint('alerts', __name__)

DB_PATH = 'monitoring.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@alerts_bp.route('/alerts', methods=['POST'])
def create_alert():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
        
    required = ['rule_name', 'metric_type', 'condition', 'threshold', 'time_window_minutes', 'notification_type', 'notification_target']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400
        
    if data['metric_type'] not in ["error_rate", "avg_latency", "rps"]:
        return jsonify({"error": "Invalid metric_type"}), 400
        
    if data['condition'] not in ["gt", "lt"]:
        return jsonify({"error": "Invalid condition"}), 400
        
    try:
        threshold = float(data['threshold'])
        if threshold <= 0:
            return jsonify({"error": "Threshold must be positive"}), 400
    except ValueError:
        return jsonify({"error": "Threshold must be a number"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO alert_rule (rule_name, service_name, metric_type, condition, threshold, time_window_minutes, notification_type, notification_target, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['rule_name'],
        data.get('service_name'),
        data['metric_type'],
        data['condition'],
        threshold,
        data['time_window_minutes'],
        data['notification_type'],
        data['notification_target'],
        1,
        time.time()
    ))
    rule_id = cursor.lastrowid
    conn.commit()
    
    cursor.execute("SELECT * FROM alert_rule WHERE id = ?", (rule_id,))
    rule = dict(cursor.fetchone())
    conn.close()
    
    return jsonify(rule), 201

@alerts_bp.route('/alerts', methods=['GET'])
def get_alerts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alert_rule")
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in rows])

@alerts_bp.route('/alerts/<int:rule_id>', methods=['DELETE'])
def delete_alert(rule_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE alert_rule SET is_active = 0 WHERE id = ?", (rule_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "deactivated"})

@alerts_bp.route('/alerts/events', methods=['GET'])
def get_events():
    limit = int(request.args.get('limit', 50))
    service_name = request.args.get('service_name')
    
    query = '''
        SELECT e.id, r.rule_name, r.service_name, e.triggered_at, e.metric_value, e.message, e.resolved
        FROM alert_event e
        JOIN alert_rule r ON e.rule_id = r.id
    '''
    params = []
    
    if service_name:
        query += " WHERE r.service_name = ?"
        params.append(service_name)
        
    query += " ORDER BY e.triggered_at DESC LIMIT ?"
    params.append(limit)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in rows])

@alerts_bp.route('/alerts/events/<int:event_id>/resolve', methods=['POST'])
def resolve_event(event_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE alert_event SET resolved = 1 WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()
    
    return jsonify({"status": "resolved"})

@alerts_bp.route('/alerts/trigger-check', methods=['GET'])
def trigger_check():
    check_all_alerts()
    return jsonify({"status": "check complete", "timestamp": time.time()})

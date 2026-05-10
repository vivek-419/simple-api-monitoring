import sqlite3
import time
from flask import Blueprint, request, jsonify
from app.services.aggregator import compute_stats, get_time_series

metrics_bp = Blueprint('metrics', __name__)

DB_PATH = 'monitoring.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS metric_entry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            method TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            response_time_ms REAL NOT NULL,
            instance_id TEXT NOT NULL,
            timestamp REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()

@metrics_bp.route('/metrics', methods=['POST'])
def add_metric():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
        
    required = ['service_name', 'endpoint', 'status_code', 'response_time_ms']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO metric_entry (service_name, endpoint, method, status_code, response_time_ms, instance_id, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        data['service_name'],
        data['endpoint'],
        data.get('method', 'UNKNOWN'),
        data['status_code'],
        data['response_time_ms'],
        data.get('instance_id', 'unknown'),
        time.time()
    ))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({"status": "ok", "id": record_id}), 201

@metrics_bp.route('/metrics/batch', methods=['POST'])
def add_metrics_batch():
    data = request.get_json()
    if not data or not isinstance(data, list):
        return jsonify({"error": "Expected a JSON array"}), 400
        
    current_time = time.time()
    rows = []
    for item in data:
        rows.append((
            item.get('service_name', 'unknown'),
            item.get('endpoint', 'unknown'),
            item.get('method', 'UNKNOWN'),
            item.get('status_code', 0),
            item.get('response_time_ms', 0.0),
            item.get('instance_id', 'unknown'),
            current_time
        ))
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT INTO metric_entry (service_name, endpoint, method, status_code, response_time_ms, instance_id, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', rows)
    conn.commit()
    inserted = cursor.rowcount
    conn.close()
    
    return jsonify({"status": "ok", "inserted": inserted})

@metrics_bp.route('/metrics/query', methods=['GET'])
def query_metrics():
    service_name = request.args.get('service_name')
    endpoint = request.args.get('endpoint')
    minutes = int(request.args.get('minutes', 60))
    limit = int(request.args.get('limit', 1000))
    
    start_time = time.time() - (minutes * 60)
    
    query = "SELECT * FROM metric_entry WHERE timestamp >= ?"
    params = [start_time]
    
    if service_name:
        query += " AND service_name = ?"
        params.append(service_name)
    if endpoint:
        query += " AND endpoint = ?"
        params.append(endpoint)
        
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    result = [dict(row) for row in rows]
    return jsonify(result)

@metrics_bp.route('/metrics/services', methods=['GET'])
def get_services():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT service_name FROM metric_entry")
    rows = cursor.fetchall()
    conn.close()
    
    services = [row['service_name'] for row in rows]
    return jsonify({"services": services})

@metrics_bp.route('/metrics/endpoints', methods=['GET'])
def get_endpoints():
    service_name = request.args.get('service_name')
    query = "SELECT DISTINCT endpoint FROM metric_entry"
    params = []
    
    if service_name:
        query += " WHERE service_name = ?"
        params.append(service_name)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    endpoints = [row['endpoint'] for row in rows]
    return jsonify({"endpoints": endpoints})

@metrics_bp.route('/metrics/stats', methods=['GET'])
def get_stats():
    service_name = request.args.get('service_name')
    endpoint = request.args.get('endpoint')
    minutes = int(request.args.get('minutes', 5))
    
    stats = compute_stats(service_name, endpoint, minutes)
    return jsonify(stats)

@metrics_bp.route('/metrics/timeseries', methods=['GET'])
def timeseries():
    service_name = request.args.get('service_name')
    minutes = int(request.args.get('minutes', 60))
    bucket_minutes = int(request.args.get('bucket_minutes', 5))
    
    series = get_time_series(service_name, minutes, bucket_minutes)
    return jsonify(series)

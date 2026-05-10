import sqlite3
import time
from datetime import datetime
from app.services.aggregator import compute_stats, get_time_series
from app.services.anomaly_detector import detect_zscore_anomaly, detect_iqr_anomaly, detect_moving_average_anomaly

DB_PATH = 'monitoring.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def send_notification(rule, actual_value):
    now = datetime.utcnow()
    message = f"ALERT: {rule['rule_name']} | Service: {rule['service_name']} | {rule['metric_type']} = {actual_value:.2f} (threshold: {rule['condition']} {rule['threshold']}) | Time: {now}"
    
    print(f"[LOG] {message}")
    
    with open('alerts.log', 'a') as f:
        f.write(f"[{now.isoformat()}] {message}\n")

def evaluate_rule(rule):
    stats = compute_stats(service_name=rule['service_name'], minutes=rule['time_window_minutes'])
    
    actual_value = 0.0
    triggered = False
    
    if rule['condition'].startswith('anomaly_'):
        # For anomalies, we need time series data
        ts_data = get_time_series(service_name=rule['service_name'], minutes=rule['time_window_minutes'], bucket_minutes=1)
        
        values = []
        for b in ts_data:
            if rule['metric_type'] == 'error_rate':
                values.append(b['error_rate'])
            elif rule['metric_type'] == 'avg_latency':
                values.append(b['avg_latency'])
            elif rule['metric_type'] == 'rps':
                values.append(b['request_count'])
                
        if len(values) > 0:
            actual_value = values[-1]
            if rule['condition'] == 'anomaly_zscore':
                res = detect_zscore_anomaly(values, threshold_z=rule['threshold'])
                triggered = res.get('is_anomaly', False)
            elif rule['condition'] == 'anomaly_iqr':
                res = detect_iqr_anomaly(values, multiplier=rule['threshold'])
                triggered = res.get('is_anomaly', False)
            elif rule['condition'] == 'anomaly_ma':
                res = detect_moving_average_anomaly(values, threshold_pct=rule['threshold'])
                triggered = res.get('is_anomaly', False)
    else:
        if rule['metric_type'] == 'error_rate':
            actual_value = stats['error_rate_percent']
        elif rule['metric_type'] == 'avg_latency':
            actual_value = stats['avg_response_time_ms']
        elif rule['metric_type'] == 'rps':
            actual_value = stats['requests_per_minute']
            
        if rule['condition'] == 'gt':
            triggered = actual_value > rule['threshold']
        elif rule['condition'] == 'lt':
            triggered = actual_value < rule['threshold']
        
    if triggered:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if an AlertEvent for this rule was triggered in the last 5 minutes
        five_mins_ago = time.time() - (5 * 60)
        cursor.execute('''
            SELECT id FROM alert_event 
            WHERE rule_id = ? AND triggered_at >= ?
        ''', (rule['id'], five_mins_ago))
        recent_event = cursor.fetchone()
        
        if not recent_event:
            message = f"{rule['metric_type']} exceeded threshold: {actual_value:.2f}"
            cursor.execute('''
                INSERT INTO alert_event (rule_id, metric_value, message, triggered_at, resolved)
                VALUES (?, ?, ?, ?, ?)
            ''', (rule['id'], actual_value, message, time.time(), 0))
            conn.commit()
            
            send_notification(rule, actual_value)
            
        conn.close()
        
    return {
        "rule_id": rule['id'],
        "triggered": triggered,
        "actual_value": actual_value
    }

def check_all_alerts():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alert_rule WHERE is_active = 1")
    rules = cursor.fetchall()
    conn.close()
    
    for rule in rules:
        try:
            result = evaluate_rule(rule)
            print(f"[AlertEngine] Checked rule '{rule['rule_name']}': value={result['actual_value']:.2f}, threshold={rule['threshold']}, triggered={result['triggered']}")
        except Exception as e:
            print(f"[AlertEngine] Error evaluating rule '{rule['rule_name']}': {e}")

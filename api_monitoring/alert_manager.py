import time
import sqlite3
from db import get_connection

CHECK_INTERVAL = 10 # seconds
TIME_WINDOW = 60 # seconds (look at the last minute of data)

def evaluate_condition(value, threshold, condition):
    if condition == '>':
        return value > threshold
    elif condition == '<':
        return value < threshold
    elif condition == '==':
        return value == threshold
    elif condition == '>=':
        return value >= threshold
    elif condition == '<=':
        return value <= threshold
    return False

def check_alerts():
    conn = get_connection()
    cursor = conn.cursor()
    
    current_time = time.time()
    start_time = current_time - TIME_WINDOW
    
    # Get all rules
    cursor.execute("SELECT * FROM alert_rules")
    rules = cursor.fetchall()
    
    for rule in rules:
        alert_id = rule['alert_id']
        metric_name = rule['metric_name']
        threshold = rule['threshold']
        condition = rule['condition']
        service_id = rule['service_id']
        notification_type = rule['notification_type']
        
        # Build query to get aggregate metric over the time window
        query = "SELECT value FROM metrics WHERE metric_name = ? AND timestamp >= ?"
        params = [metric_name, start_time]
        
        if service_id:
            query += " AND service_id = ?"
            params.append(service_id)
            
        cursor.execute(query, params)
        metrics = cursor.fetchall()
        
        if not metrics:
            continue
            
        values = [m['value'] for m in metrics]
        
        # Aggregate based on metric type
        if metric_name == 'response_time_ms':
            # Average response time
            agg_value = sum(values) / len(values)
        elif metric_name == 'request_count' or metric_name == 'error_count':
            # Sum of counts
            agg_value = sum(values)
        else:
            # Default to average
            agg_value = sum(values) / len(values)
            
        if evaluate_condition(agg_value, threshold, condition):
            print(f"🚨 ALERT TRIGGERED: {metric_name} is {agg_value:.2f} (Rule: {condition} {threshold}) for service {service_id or 'ALL'}")
            
            # Send notification mock
            if notification_type == 'email':
                print("📧 Sending Email Notification...")
            elif notification_type == 'sms':
                print("📱 Sending SMS Notification...")
                
            # Log to DB
            cursor.execute('''
                INSERT INTO triggered_alerts (alert_id, metric_name, value, threshold, condition, timestamp, service_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (alert_id, metric_name, agg_value, threshold, condition, current_time, service_id))
            conn.commit()

    conn.close()

if __name__ == "__main__":
    print("Starting Alert Manager...")
    print(f"Checking rules every {CHECK_INTERVAL} seconds over a {TIME_WINDOW}s sliding window.")
    while True:
        try:
            check_alerts()
        except Exception as e:
            print(f"Error checking alerts: {e}")
        time.sleep(CHECK_INTERVAL)

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import time
from db import get_connection, init_db

# Initialize database on startup
init_db()

app = FastAPI(title="Metrics Ingestion & Query Service")

# ----------------- Models -----------------
class MetricPayload(BaseModel):
    metric_name: str
    timestamp: float
    value: float
    service_id: str
    endpoint: Optional[str] = None

class AlertRulePayload(BaseModel):
    metric_name: str
    threshold: float
    condition: str  # '>', '<', '=='
    notification_type: str
    service_id: Optional[str] = None

# ----------------- APIs -----------------

@app.post("/metrics")
def push_metrics(metrics: List[MetricPayload]):
    """Ingest a batch of metrics and store them in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    data = [(m.metric_name, m.timestamp, m.value, m.service_id, m.endpoint) for m in metrics]
    
    cursor.executemany('''
        INSERT INTO metrics (metric_name, timestamp, value, service_id, endpoint)
        VALUES (?, ?, ?, ?, ?)
    ''', data)
    
    conn.commit()
    conn.close()
    return {"status": "success", "inserted": len(metrics)}

@app.get("/metrics/query")
def query_metrics(
    metric_name: str, 
    service_id: Optional[str] = None, 
    start_time: Optional[float] = None, 
    end_time: Optional[float] = None
):
    """Query metrics for the dashboard visualization."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM metrics WHERE metric_name = ?"
    params = [metric_name]
    
    if service_id:
        query += " AND service_id = ?"
        params.append(service_id)
    if start_time:
        query += " AND timestamp >= ?"
        params.append(start_time)
    if end_time:
        query += " AND timestamp <= ?"
        params.append(end_time)
        
    query += " ORDER BY timestamp ASC"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    return {"metrics": [dict(row) for row in rows]}

@app.post("/alerts")
def create_alert_rule(rule: AlertRulePayload):
    """Configure a new alert rule."""
    conn = get_connection()
    cursor = conn.cursor()
    
    current_time = time.time()
    cursor.execute('''
        INSERT INTO alert_rules (metric_name, threshold, condition, notification_type, created_at, service_id)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (rule.metric_name, rule.threshold, rule.condition, rule.notification_type, current_time, rule.service_id))
    
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Alert rule created"}

@app.get("/alerts")
def get_alerts():
    """Get all configured alert rules."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alert_rules")
    rows = cursor.fetchall()
    conn.close()
    return {"rules": [dict(row) for row in rows]}

@app.get("/alerts/triggered")
def get_triggered_alerts(limit: int = Query(50, ge=1, le=100)):
    """Get history of triggered alerts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM triggered_alerts ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return {"triggered_alerts": [dict(row) for row in rows]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

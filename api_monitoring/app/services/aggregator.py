import sqlite3
import time
from datetime import datetime
import os

DB_PATH = 'monitoring.db'

def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def compute_stats(service_name=None, endpoint=None, minutes=5):
    start_time = time.time() - (minutes * 60)
    
    query = "SELECT status_code, response_time_ms FROM metric_entry WHERE timestamp >= ?"
    params = [start_time]
    
    if service_name:
        query += " AND service_name = ?"
        params.append(service_name)
    if endpoint:
        query += " AND endpoint = ?"
        params.append(endpoint)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    total_requests = len(rows)
    
    if total_requests == 0:
        return {
            "total_requests": 0,
            "requests_per_minute": 0.0,
            "avg_response_time_ms": 0.0,
            "p95_response_time_ms": 0.0,
            "error_count": 0,
            "error_rate_percent": 0.0,
            "status_code_breakdown": {
                "2xx": 0,
                "4xx": 0,
                "5xx": 0
            },
            "service_name": service_name or "all",
            "endpoint": endpoint or "all",
            "window_minutes": minutes
        }
        
    response_times = []
    error_count = 0
    status_breakdown = {"2xx": 0, "4xx": 0, "5xx": 0}
    
    for row in rows:
        rt = row['response_time_ms']
        code = row['status_code']
        response_times.append(rt)
        
        if code >= 400:
            error_count += 1
            
        if 200 <= code < 300:
            status_breakdown["2xx"] += 1
        elif 400 <= code < 500:
            status_breakdown["4xx"] += 1
        elif code >= 500:
            status_breakdown["5xx"] += 1
            
    response_times.sort()
    p95_index = int(len(response_times) * 0.95)
    # Ensure index is within bounds
    if p95_index >= len(response_times):
        p95_index = len(response_times) - 1
        
    p95_response_time_ms = response_times[p95_index]
    avg_response_time_ms = sum(response_times) / total_requests
    requests_per_minute = total_requests / minutes
    error_rate_percent = (error_count / total_requests) * 100
    
    return {
        "total_requests": total_requests,
        "requests_per_minute": float(requests_per_minute),
        "avg_response_time_ms": float(avg_response_time_ms),
        "p95_response_time_ms": float(p95_response_time_ms),
        "error_count": error_count,
        "error_rate_percent": float(error_rate_percent),
        "status_code_breakdown": status_breakdown,
        "service_name": service_name or "all",
        "endpoint": endpoint or "all",
        "window_minutes": minutes
    }

def get_time_series(service_name=None, minutes=60, bucket_minutes=5):
    end_time = time.time()
    start_time = end_time - (minutes * 60)
    
    query = "SELECT timestamp, status_code, response_time_ms FROM metric_entry WHERE timestamp >= ?"
    params = [start_time]
    
    if service_name:
        query += " AND service_name = ?"
        params.append(service_name)
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Create buckets
    bucket_seconds = bucket_minutes * 60
    buckets = {}
    
    # Initialize all buckets in the range
    current_bucket = start_time
    while current_bucket <= end_time:
        buckets[current_bucket] = {"response_times": [], "errors": 0, "count": 0}
        current_bucket += bucket_seconds
        
    for row in rows:
        ts = row['timestamp']
        # Find which bucket this belongs to
        bucket_ts = start_time + ((ts - start_time) // bucket_seconds) * bucket_seconds
        if bucket_ts in buckets:
            buckets[bucket_ts]["count"] += 1
            buckets[bucket_ts]["response_times"].append(row['response_time_ms'])
            if row['status_code'] >= 400:
                buckets[bucket_ts]["errors"] += 1
                
    result = []
    for bucket_ts in sorted(buckets.keys()):
        data = buckets[bucket_ts]
        count = data["count"]
        
        if count > 0:
            avg_latency = sum(data["response_times"]) / count
            error_rate = (data["errors"] / count) * 100
        else:
            avg_latency = 0.0
            error_rate = 0.0
            
        iso_timestamp = datetime.fromtimestamp(bucket_ts).isoformat() + "Z"
        
        result.append({
            "bucket_start": iso_timestamp,
            "avg_latency": float(avg_latency),
            "error_rate": float(error_rate),
            "request_count": count
        })
        
    return result

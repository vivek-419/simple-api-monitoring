# End-to-End API Monitoring System

This project is a scalable, real-time API monitoring and alerting system designed to track the health of microservices. It intercepts HTTP traffic to capture vital metrics (latency, error rates, request volume), buffers them for efficient database ingestion, automatically evaluates thresholds, and triggers notifications—all visualized on a beautiful, auto-refreshing dashboard.

## Setup Instructions

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   *(Or activate the virtual environment if it was created for you).*

2. Start the entire system (Main Server, 3 Demo Microservices, and Traffic Simulator):
   ```bash
   python start_all.py
   ```

3. Open your browser and navigate to the dashboard:
   [http://localhost:5005/](http://localhost:5005/)

## System Architecture Decisions

### 1. SQLite with Timestamp Indexing vs True Time-Series DB
While enterprise systems use databases like Prometheus or InfluxDB for metrics, this system approximates a TSDB using SQLite by indexing and querying against Unix timestamps. At a smaller scale, querying bounded timestamp ranges (e.g. `timestamp >= start_time`) and bucketizing the data in memory (within `aggregator.py`) provides sufficient performance and simplifies deployment without requiring external dependencies like an InfluxDB server.

### 2. Non-blocking Background Threading in the Collector
The `MetricsCollectorMiddleware` wraps every incoming request to calculate metrics, but it `POST`s the data to the ingestion server using a daemon thread. This is a critical design choice because monitoring overhead must never degrade the main application's response time or availability. If the ingestion server goes down, the background thread safely catches the exception and exits silently without crashing the user's request.

### 3. Real-time Streaming vs Batch Polling Trade-off
This system evaluates alerts by having a background `APScheduler` job wake up every 30 seconds and poll the recent data (`check_all_alerts()`). 
**Trade-off:** True real-time stream processing evaluates each metric as it arrives, providing sub-second alert times but at a massive computational cost. Our batch polling approach is highly scalable and reduces database load (evaluating aggregations in batches), but introduces up to 30 seconds of latency between a failure occurring and an alert firing.

## API Endpoints

| Method | Path | Description | Example Request / Response |
|--------|------|-------------|----------------------------|
| `GET` | `/health` | Check monitoring server health. | **Req:** `GET /health`<br>**Res:** `{"status": "ok", "timestamp": "2026-05-05T..."}` |
| `POST` | `/metrics` | Ingest a single metric event. | **Req:** `{"service_name": "auth", "endpoint": "/login", "status_code": 200, "response_time_ms": 45}`<br>**Res:** `{"status": "ok", "id": 1}` |
| `POST` | `/metrics/batch` | Ingest an array of metric events. | **Req:** `[{"service_name": "auth", ...}, {...}]`<br>**Res:** `{"status": "ok", "inserted": 2}` |
| `GET` | `/metrics/query` | Raw metric records query. | **Req:** `GET /metrics/query?minutes=60`<br>**Res:** `[{"service_name": "auth", ...}]` |
| `GET` | `/metrics/services`| Get unique registered services. | **Req:** `GET /metrics/services`<br>**Res:** `{"services": ["auth-service", "payment-service"]}` |
| `GET` | `/metrics/stats` | Aggregated stats for the dashboard. | **Req:** `GET /metrics/stats?minutes=5`<br>**Res:** `{"avg_response_time_ms": 120, "error_rate_percent": 2.5, ...}` |
| `GET` | `/metrics/timeseries`| Bucketized time-series chart data. | **Req:** `GET /metrics/timeseries?minutes=60`<br>**Res:** `[{"bucket_start": "2026-05...", "avg_latency": 150...}]` |
| `POST` | `/alerts` | Create a new alert rule. | **Req:** `{"rule_name": "Test", "metric_type": "rps", "condition": "gt", "threshold": 100, ...}`<br>**Res:** `{"id": 4, "rule_name": "Test", ...}` |
| `GET` | `/alerts` | Get all active alert rules. | **Req:** `GET /alerts`<br>**Res:** `[{"rule_name": "High Latency", ...}]` |
| `DELETE`| `/alerts/<id>` | Soft-delete an alert rule. | **Req:** `DELETE /alerts/1`<br>**Res:** `{"status": "deactivated"}` |
| `GET` | `/alerts/events` | Get recent triggered alert events. | **Req:** `GET /alerts/events`<br>**Res:** `[{"rule_name": "High Error Rate", "resolved": 0, ...}]` |
| `POST` | `/alerts/events/<id>/resolve` | Mark an alert event as resolved. | **Req:** `POST /alerts/events/5/resolve`<br>**Res:** `{"status": "resolved"}` |

## Dashboard Preview
<img width="468" height="305" alt="image" src="https://github.com/user-attachments/assets/9826f93e-3464-48e0-9f3b-a780d834d921" />
<img width="468" height="305" alt="image" src="https://github.com/user-attachments/assets/98944d92-cf00-40ce-b651-2fb27b81be32" />
<img width="468" height="305" alt="image" src="https://github.com/user-attachments/assets/bae56ace-5f8c-46ac-b915-5767b84fadeb" />
<img width="468" height="305" alt="image" src="https://github.com/user-attachments/assets/8e0188d5-cd73-4ef4-b6fd-6b1c868fec7b" />





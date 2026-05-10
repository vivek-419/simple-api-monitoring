from fastapi import FastAPI, Request, BackgroundTasks
import time
import random
import requests
import asyncio
from typing import List, Dict

app = FastAPI(title="Dummy API Service (Producer)")

# Configuration
SERVICE_ID = "payment-service"
INGESTION_SERVER_URL = "http://localhost:8000/metrics"
METRIC_BUFFER: List[Dict] = []
BATCH_SIZE = 10
FLUSH_INTERVAL = 5 # seconds

def push_metrics_to_server():
    """Background task to push buffered metrics to the ingestion service."""
    global METRIC_BUFFER
    if not METRIC_BUFFER:
        return

    # Take a snapshot and clear buffer
    metrics_to_send = METRIC_BUFFER[:]
    METRIC_BUFFER.clear()

    try:
        response = requests.post(INGESTION_SERVER_URL, json=metrics_to_send)
        if response.status_code != 200:
            print(f"Failed to push metrics: {response.text}")
    except Exception as e:
        print(f"Error pushing metrics to server: {e}")

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    """Middleware to collect metrics (latency, count, errors) for every request."""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise e
    finally:
        process_time = (time.time() - start_time) * 1000 # Convert to milliseconds
        endpoint = request.url.path
        
        # 1. Record Response Time
        METRIC_BUFFER.append({
            "metric_name": "response_time_ms",
            "timestamp": time.time(),
            "value": process_time,
            "service_id": SERVICE_ID,
            "endpoint": endpoint
        })
        
        # 2. Record Request Count
        METRIC_BUFFER.append({
            "metric_name": "request_count",
            "timestamp": time.time(),
            "value": 1,
            "service_id": SERVICE_ID,
            "endpoint": endpoint
        })
        
        # 3. Record Error Rate (if 4xx or 5xx)
        if status_code >= 400:
            METRIC_BUFFER.append({
                "metric_name": "error_count",
                "timestamp": time.time(),
                "value": 1,
                "service_id": SERVICE_ID,
                "endpoint": endpoint
            })

    return response

# Periodic flush mechanism
@app.on_event("startup")
async def startup_event():
    async def flush_loop():
        while True:
            await asyncio.sleep(FLUSH_INTERVAL)
            # Run blocking push_metrics in a thread
            # For simplicity in this dummy service, we just call it directly
            push_metrics_to_server()

    asyncio.create_task(flush_loop())

# ----------------- Dummy Endpoints -----------------

@app.get("/checkout")
def checkout():
    # Simulate processing time
    time.sleep(random.uniform(0.05, 0.2))
    return {"message": "Checkout successful"}

@app.get("/inventory")
def inventory():
    # Simulate slightly slower processing
    time.sleep(random.uniform(0.1, 0.5))
    return {"items": ["item1", "item2"]}

@app.get("/flaky")
def flaky():
    # Simulate 20% error rate
    if random.random() < 0.2:
        # Also simulate a slow failure
        time.sleep(random.uniform(0.5, 1.5))
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Internal Server Error")
    
    time.sleep(random.uniform(0.01, 0.05))
    return {"message": "Flaky endpoint worked this time"}

if __name__ == "__main__":
    import uvicorn
    # Run the producer on a different port than the ingestion server
    uvicorn.run(app, host="0.0.0.0", port=8001)

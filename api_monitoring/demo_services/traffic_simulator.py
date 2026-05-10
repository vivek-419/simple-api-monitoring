import time
import random
import requests
from datetime import datetime

SERVICES = {
    "auth": {
        "url_base": "http://localhost:5001",
        "endpoints": [
            ("POST", "/api/login", 0.6),
            ("GET", "/api/verify-token", 0.3),
            ("POST", "/api/logout", 0.1)
        ]
    },
    "payment": {
        "url_base": "http://localhost:5002",
        "endpoints": [
            ("POST", "/api/charge", 0.5),
            ("GET", "/api/transactions", 0.4),
            ("POST", "/api/refund", 0.1)
        ]
    },
    "search": {
        "url_base": "http://localhost:5003",
        "endpoints": [
            ("GET", "/api/search?q=demo", 0.6),
            ("GET", "/api/suggest", 0.3),
            ("GET", "/api/trending", 0.1)
        ]
    }
}

SERVICE_WEIGHTS = {"auth": 0.40, "payment": 0.35, "search": 0.25}

def pick_service():
    services = list(SERVICE_WEIGHTS.keys())
    weights = list(SERVICE_WEIGHTS.values())
    return random.choices(services, weights=weights, k=1)[0]

def pick_endpoint(service_key):
    endpoints = SERVICES[service_key]["endpoints"]
    methods = [e[0] for e in endpoints]
    paths = [e[1] for e in endpoints]
    weights = [e[2] for e in endpoints]
    idx = random.choices(range(len(endpoints)), weights=weights, k=1)[0]
    return methods[idx], paths[idx]

def run_simulation():
    print("[Simulator] Starting traffic simulation...")
    
    total_sent = 0
    total_errors = 0
    errors_by_service = {"auth": 0, "payment": 0, "search": 0}
    
    start_time = time.time()
    last_summary_time = start_time
    
    while True:
        now = time.time()
        
        # Check spike (every 60s, lasts 15s)
        is_spike = False
        if int(now - start_time) % 60 < 15 and (now - start_time) > 10:
            is_spike = True
            
        # Check degradation (every 120s, lasts 20s)
        is_degraded = False
        if int(now - start_time) % 120 < 20 and (now - start_time) > 10:
            is_degraded = True

        service_key = pick_service()
        method, path = pick_endpoint(service_key)
        url = SERVICES[service_key]["url_base"] + path
        
        headers = {}
        if is_degraded and service_key == "payment":
            headers['X-Latency-Degradation'] = '1'
            
        req_start = time.time()
        status_code = 0
        try:
            if method == "GET":
                res = requests.get(url, headers=headers, timeout=5)
            else:
                res = requests.post(url, headers=headers, json={}, timeout=5)
            status_code = res.status_code
        except Exception:
            status_code = 500
            
        req_time_ms = int((time.time() - req_start) * 1000)
        
        total_sent += 1
        if status_code >= 400:
            total_errors += 1
            errors_by_service[service_key] += 1
            
        degraded_flag = " [DEGRADED]" if is_degraded and service_key == "payment" else ""
        print(f"[Simulator] {method} {url} → {status_code} in {req_time_ms}ms{degraded_flag}")
        
        if now - last_summary_time >= 30:
            print("\n--- [Simulator Summary] ---")
            print(f"Total Requests: {total_sent} | Total Errors: {total_errors}")
            print(f"Errors by Service: {errors_by_service}")
            print("---------------------------\n")
            last_summary_time = now
            
        if is_spike:
            time.sleep(0.01)
        else:
            time.sleep(random.uniform(0.1, 0.5))

if __name__ == '__main__':
    time.sleep(3)
    try:
        run_simulation()
    except KeyboardInterrupt:
        print("\n[Simulator] Stopped.")

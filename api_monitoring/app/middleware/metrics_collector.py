import time
import threading
import requests
from flask import request

class MetricsCollectorMiddleware:
    def __init__(self, app, service_name="default-service", instance_id="instance-1", metrics_url="http://localhost:5005/metrics"):
        self.app = app
        self.service_name = service_name
        self.instance_id = instance_id
        self.metrics_url = metrics_url
        
        # Register hooks
        self.app.before_request(self.before_request)
        self.app.after_request(self.after_request)

    def before_request(self):
        # Store start time in the request context
        request.start_time = time.time()

    def after_request(self, response):
        # Skip metrics and dashboard routes
        if request.path.startswith('/metrics') or request.path.startswith('/dashboard'):
            return response
            
        start_time = getattr(request, 'start_time', time.time())
        response_time_ms = (time.time() - start_time) * 1000
        
        payload = {
            "service_name": self.service_name,
            "endpoint": request.path,
            "method": request.method,
            "status_code": response.status_code,
            "response_time_ms": response_time_ms,
            "instance_id": self.instance_id
        }
        
        # POST metrics asynchronously
        threading.Thread(target=self._send_metrics, args=(payload,), daemon=True).start()
        
        return response

    def _send_metrics(self, payload):
        try:
            requests.post(self.metrics_url, json=payload, timeout=2)
        except Exception:
            # Handle connection errors silently so monitoring doesn't crash the main app
            pass

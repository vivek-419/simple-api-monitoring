import time
import random
import uuid
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify
from app.middleware.metrics_collector import MetricsCollectorMiddleware

app = Flask(__name__)
service_name = "auth-service"
instance_id = f"{service_name}-instance-{uuid.uuid4().hex[:4]}"

# Install middleware
MetricsCollectorMiddleware(app, service_name=service_name, instance_id=instance_id)

@app.route('/api/login', methods=['POST'])
def login():
    time.sleep(random.uniform(0.02, 0.12)) # 20-120ms
    r = random.random()
    if r < 0.80:
        return jsonify({"token": "abc123", "user": "user@example.com"}), 200
    elif r < 0.95:
        return jsonify({"error": "invalid credentials"}), 401
    else:
        time.sleep(1.5)
        return jsonify({"error": "auth service error"}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    time.sleep(random.uniform(0.01, 0.03))
    return jsonify({"status": "logged out"}), 200

@app.route('/api/verify-token', methods=['GET'])
def verify_token():
    time.sleep(random.uniform(0.015, 0.05))
    r = random.random()
    if r < 0.90:
        return jsonify({"status": "valid"}), 200
    else:
        return jsonify({"error": "forbidden"}), 403

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": service_name}), 200

if __name__ == '__main__':
    app.run(port=5001)

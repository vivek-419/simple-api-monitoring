import time
import random
import uuid
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request
from app.middleware.metrics_collector import MetricsCollectorMiddleware

app = Flask(__name__)
service_name = "payment-service"
instance_id = f"{service_name}-instance-{uuid.uuid4().hex[:4]}"

MetricsCollectorMiddleware(app, service_name=service_name, instance_id=instance_id)

@app.route('/api/charge', methods=['POST'])
def charge():
    extra_sleep = 0
    if request.headers.get('X-Latency-Degradation') == '1':
        extra_sleep = 0.6
        
    time.sleep(random.uniform(0.08, 0.3) + extra_sleep)
    r = random.random()
    if r < 0.85:
        return jsonify({"transaction_id": uuid.uuid4().hex, "amount": random.uniform(10, 1000)}), 200
    elif r < 0.95:
        return jsonify({"error": "payment declined"}), 402
    else:
        return jsonify({"error": "internal error"}), 500

@app.route('/api/transactions', methods=['GET'])
def transactions():
    time.sleep(random.uniform(0.04, 0.1))
    return jsonify([{"tx": uuid.uuid4().hex} for _ in range(5)]), 200

@app.route('/api/refund', methods=['POST'])
def refund():
    time.sleep(random.uniform(0.1, 0.4))
    r = random.random()
    if r < 0.70:
        return jsonify({"status": "refunded"}), 200
    elif r < 0.90:
        return jsonify({"error": "bad request"}), 400
    else:
        return jsonify({"error": "refund failed"}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": service_name}), 200

if __name__ == '__main__':
    app.run(port=5002)

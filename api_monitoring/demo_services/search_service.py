import time
import random
import uuid
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request
from app.middleware.metrics_collector import MetricsCollectorMiddleware

app = Flask(__name__)
service_name = "search-service"
instance_id = f"{service_name}-instance-{uuid.uuid4().hex[:4]}"

MetricsCollectorMiddleware(app, service_name=service_name, instance_id=instance_id)

@app.route('/api/search', methods=['GET'])
def search():
    time.sleep(random.uniform(0.03, 0.2))
    r = random.random()
    q = request.args.get('q', 'test')
    if r < 0.95:
        return jsonify({"results": [], "total": random.randint(0, 1000), "query": q}), 200
    else:
        return jsonify({"error": "search engine unavailable"}), 500

@app.route('/api/suggest', methods=['GET'])
def suggest():
    time.sleep(random.uniform(0.01, 0.03))
    return jsonify({"suggestions": ["item1", "item2"]}), 200

@app.route('/api/trending', methods=['GET'])
def trending():
    time.sleep(random.uniform(0.02, 0.06))
    return jsonify({"trending": ["trend1", "trend2"]}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "service": service_name}), 200

if __name__ == '__main__':
    app.run(port=5003)

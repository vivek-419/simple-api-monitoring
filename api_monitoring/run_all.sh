#!/bin/bash

echo "Starting API Monitoring System..."

# Start the Ingestion Server (Port 8000)
python3 server.py &
SERVER_PID=$!

# Wait a moment for server to start
sleep 2

# Start the Producer Service (Port 8001)
python3 producer.py &
PRODUCER_PID=$!

# Start the Alert Manager
python3 alert_manager.py &
ALERT_MANAGER_PID=$!

# Start the Streamlit Dashboard (Port 8501 by default)
streamlit run dashboard.py &
DASHBOARD_PID=$!

echo "All services started."
echo "Press Ctrl+C to stop all services."

# Wait for Ctrl+C
trap "echo 'Stopping all services...'; kill $SERVER_PID $PRODUCER_PID $ALERT_MANAGER_PID $DASHBOARD_PID; exit" INT

wait

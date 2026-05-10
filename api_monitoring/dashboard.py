import streamlit as st
import sqlite3
import pandas as pd
import time
from db import get_connection

# Page Config
st.set_page_config(page_title="API Monitoring Dashboard", layout="wide", page_icon="📊")
st.title("📊 API Monitoring Dashboard")

# Auto-refresh
st_autorefresh = st.empty()
refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 5, 60, 10)

def load_data():
    conn = get_connection()
    
    # Load last 5 minutes of data
    time_window = time.time() - (5 * 60)
    
    metrics_df = pd.read_sql_query(
        "SELECT * FROM metrics WHERE timestamp >= ?", 
        conn, 
        params=(time_window,)
    )
    
    alerts_df = pd.read_sql_query(
        "SELECT * FROM triggered_alerts ORDER BY timestamp DESC LIMIT 20", 
        conn
    )
    
    conn.close()
    
    # Convert timestamps to datetime for pandas charting
    if not metrics_df.empty:
        metrics_df['datetime'] = pd.to_datetime(metrics_df['timestamp'], unit='s')
        
    if not alerts_df.empty:
        alerts_df['datetime'] = pd.to_datetime(alerts_df['timestamp'], unit='s')
        
    return metrics_df, alerts_df

metrics_df, alerts_df = load_data()

# Layout
col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 Traffic (Requests)")
    if not metrics_df.empty:
        req_df = metrics_df[metrics_df['metric_name'] == 'request_count']
        if not req_df.empty:
            # Resample to 5-second intervals and sum
            req_chart_data = req_df.set_index('datetime').resample('5S')['value'].sum().reset_index()
            st.line_chart(req_chart_data, x='datetime', y='value', use_container_width=True)
        else:
            st.info("No request data available in the last 5 minutes.")
    else:
        st.info("No metrics data available.")

with col2:
    st.subheader("⏱️ Response Time (ms)")
    if not metrics_df.empty:
        res_df = metrics_df[metrics_df['metric_name'] == 'response_time_ms']
        if not res_df.empty:
            # Resample to 5-second intervals and average
            res_chart_data = res_df.set_index('datetime').resample('5S')['value'].mean().reset_index()
            st.line_chart(res_chart_data, x='datetime', y='value', use_container_width=True)
        else:
            st.info("No response time data available.")
    else:
        st.info("No metrics data available.")

st.divider()

st.subheader("🚨 Recent Alerts")
if not alerts_df.empty:
    display_df = alerts_df[['datetime', 'service_id', 'metric_name', 'value', 'condition', 'threshold']].copy()
    display_df.columns = ['Time', 'Service', 'Metric', 'Actual Value', 'Condition', 'Threshold']
    
    # Apply a quick style to highlight the rows
    def highlight_row(row):
        return ['background-color: #ffcccc' if i % 2 == 0 else 'background-color: #ffe6e6' for i in range(len(row))]
    
    st.dataframe(display_df, use_container_width=True)
else:
    st.success("No alerts triggered recently. System is healthy! ✅")

# Force Streamlit to rerun periodically
time.sleep(refresh_rate)
st.rerun()

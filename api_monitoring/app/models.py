"""
This file acts as documentation for the AlertRule model, as our implementation
uses raw SQLite inside app/__init__.py for maximum portability without an ORM.

AlertRule Schema:
- id: INTEGER PRIMARY KEY
- rule_name: TEXT NOT NULL
- service_name: TEXT (nullable)
- metric_type: TEXT NOT NULL ('error_rate', 'avg_latency', 'rps')
- condition: TEXT NOT NULL ('gt', 'lt', 'anomaly_zscore', 'anomaly_iqr', 'anomaly_ma')
- threshold: REAL NOT NULL
- time_window_minutes: INTEGER NOT NULL
- is_active: INTEGER DEFAULT 1
- created_at: REAL NOT NULL
"""

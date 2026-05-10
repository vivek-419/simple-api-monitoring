from app import create_app
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.alert_engine import check_all_alerts
from app.__init__ import cleanup_old_metrics
import logging

# Disable verbose APScheduler logging
logging.getLogger('apscheduler').setLevel(logging.WARNING)

app = create_app()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=check_all_alerts, trigger="interval", seconds=30)
    scheduler.add_job(func=cleanup_old_metrics, trigger="interval", hours=1)
    scheduler.start()

if __name__ == '__main__':
    start_scheduler()
    # use_reloader=False prevents double-starting the scheduler in debug mode
    app.run(host='0.0.0.0', port=5005, use_reloader=False)

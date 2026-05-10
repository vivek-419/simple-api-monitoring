import subprocess
import time
import sys

def start_process(cmd, name):
    print(f"Starting {name}...")
    # Hide verbose Flask stdout to keep simulator output clean, but keep stderr for errors
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

processes = []

try:
    print("====================================")
    print("🚀 API Monitoring End-to-End Demo")
    print("====================================")
    
    # 1. Start main app
    p_main = start_process([sys.executable, "run.py"], "Main App (Port 5005)")
    processes.append(p_main)
    
    time.sleep(2)
    
    # 2. Start demo services
    p_auth = start_process([sys.executable, "demo_services/auth_service.py"], "Auth Service (Port 5001)")
    processes.append(p_auth)
    
    p_pay = start_process([sys.executable, "demo_services/payment_service.py"], "Payment Service (Port 5002)")
    processes.append(p_pay)
    
    p_search = start_process([sys.executable, "demo_services/search_service.py"], "Search Service (Port 5003)")
    processes.append(p_search)
    
    print("\n✅ All services started successfully!")
    print("  - Main App:        http://localhost:5005")
    print("  - Auth Service:    http://localhost:5001")
    print("  - Payment Service: http://localhost:5002")
    print("  - Search Service:  http://localhost:5003")
    print("\nWaiting 3 seconds before starting traffic simulator...\n")
    time.sleep(3)
    
    # 3. Start traffic simulator (in foreground to see logs)
    print("Starting Traffic Simulator...")
    sim = subprocess.Popen([sys.executable, "demo_services/traffic_simulator.py"])
    processes.append(sim)
    
    sim.wait()
    
except KeyboardInterrupt:
    print("\n🛑 Terminating all processes...")
finally:
    for p in processes:
        p.terminate()
        try:
            p.wait(timeout=2)
        except:
            p.kill()
    print("All processes stopped.")

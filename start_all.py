"""
Ek command se sab kuch start: 3 workers + load balancer + Streamlit dashboard.
    python start_all.py
Band karne ke liye Ctrl+C.
(Failure demo ke liye har cheez alag terminal me chalana better hai - README dekho.)
"""
import subprocess
import sys
import time

py = sys.executable
procs = []

try:
    for port in (5001, 5002, 5003):
        procs.append(subprocess.Popen([py, "worker.py", str(port)]))
    time.sleep(2)
    procs.append(subprocess.Popen([py, "app.py"]))
    time.sleep(2)
    procs.append(subprocess.Popen([py, "-m", "streamlit", "run", "dashboard.py"]))
    print("\nSab start ho gaya. Dashboard: http://localhost:8501  (Ctrl+C se band)\n")
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down...")
finally:
    for p in procs:
        p.terminate()
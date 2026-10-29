"""Teeno workers ek saath start karne ke liye (Ctrl+C se band)."""
import subprocess, sys, time

ports = [5001, 5002, 5003]
procs = [subprocess.Popen([sys.executable, "worker.py", str(p)]) for p in ports]
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    for p in procs:
        p.terminate()
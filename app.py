"""
Load Balancer (client-facing API) - port 5000
Round Robin + failure handling + background health checks.

Run:  python app.py
Different machines pe workers hon to WORKERS list me IP daalo,
ya env var:  WORKERS="http://192.168.1.5:5001,http://192.168.1.6:5001"
"""
import os
import time
import threading
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

DEFAULT_WORKERS = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
]
WORKER_URLS = os.environ.get("WORKERS", ",".join(DEFAULT_WORKERS)).split(",")

HEALTH_INTERVAL = 5      # seconds
REQUEST_TIMEOUT = 5      # seconds

lock = threading.Lock()
rr_index = 0
task_counter = 0
history = []             # in-memory task history

workers = {
    url: {"url": url, "alive": True, "tasks_handled": 0, "failures": 0,
          "last_checked": None}
    for url in WORKER_URLS
}


# ---------- Round Robin selection ----------
def get_candidate_order():
    """Round robin sirf alive workers ke beech; dead workers last fallback."""
    global rr_index
    alive = [u for u, w in workers.items() if w["alive"]]
    dead = [u for u, w in workers.items() if not w["alive"]]
    with lock:
        idx = rr_index
        rr_index += 1
    if alive:
        start = idx % len(alive)
        alive = alive[start:] + alive[:start]
    return alive + dead


# ---------- Health checker (background thread) ----------
def health_loop():
    while True:
        for url, w in workers.items():
            try:
                r = requests.get(f"{url}/health", timeout=2)
                w["alive"] = r.status_code == 200
            except requests.RequestException:
                w["alive"] = False
            w["last_checked"] = time.strftime("%H:%M:%S")
        time.sleep(HEALTH_INTERVAL)


# ---------- Routes ----------
@app.route("/submit", methods=["POST"])
def submit():
    global task_counter
    body = request.get_json(silent=True) or {}
    if "task" not in body:
        return jsonify({"error": "JSON body me 'task' aur 'data' do"}), 400

    with lock:
        task_counter += 1
        task_id = task_counter

    attempts = []
    t0 = time.time()

    for url in get_candidate_order():
        try:
            r = requests.post(f"{url}/execute", json=body, timeout=REQUEST_TIMEOUT)
        except requests.RequestException:
            # Worker unavailable -> mark down, next worker try karo (failover)
            workers[url]["alive"] = False
            workers[url]["failures"] += 1
            attempts.append({"worker": url, "outcome": "unreachable"})
            continue

        workers[url]["alive"] = True
        payload = r.json()

        if r.status_code == 200:
            with lock:
                workers[url]["tasks_handled"] += 1
            attempts.append({"worker": url, "outcome": "success"})
            record = {
                "task_id": task_id,
                "task": body["task"],
                "data": body.get("data"),
                "status": "completed",
                "handled_by": payload["worker"],
                "result": payload["result"],
                "attempts": attempts,
                "time_ms": round((time.time() - t0) * 1000),
                "timestamp": time.strftime("%H:%M:%S"),
            }
            history.append(record)
            return jsonify(record), 200

        # Task hi galat hai (400/422) -> dusre worker pe retry ka fayda nahi
        attempts.append({"worker": url, "outcome": "task_error"})
        record = {
            "task_id": task_id, "task": body["task"], "data": body.get("data"),
            "status": "failed", "error": payload.get("error"),
            "attempts": attempts, "timestamp": time.strftime("%H:%M:%S"),
        }
        history.append(record)
        return jsonify(record), r.status_code

    record = {
        "task_id": task_id, "task": body["task"], "data": body.get("data"),
        "status": "failed", "error": "All workers unavailable",
        "attempts": attempts, "timestamp": time.strftime("%H:%M:%S"),
    }
    history.append(record)
    return jsonify(record), 503


@app.route("/workers", methods=["GET"])
def get_workers():
    return jsonify(list(workers.values()))


@app.route("/history", methods=["GET"])
def get_history():
    limit = request.args.get("limit", type=int)
    return jsonify(history[-limit:] if limit else history)


@app.route("/stats", methods=["GET"])
def stats():
    done = [h for h in history if h["status"] == "completed"]
    return jsonify({
        "total_submitted": task_counter,
        "completed": len(done),
        "failed": len(history) - len(done),
        "workers_alive": sum(w["alive"] for w in workers.values()),
        "workers_total": len(workers),
        "per_worker": {u: w["tasks_handled"] for u, w in workers.items()},
    })


if __name__ == "__main__":
    threading.Thread(target=health_loop, daemon=True).start()
    print("Load balancer on port 5000 | workers:", WORKER_URLS)
    app.run(host="0.0.0.0", port=5000, threaded=True)
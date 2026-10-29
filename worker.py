"""
Worker server.
Run:  python worker.py 5001
Har worker ek independent process hai jo tasks execute karta hai.
"""
import sys
import time
import math
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5001
WORKER_ID = f"worker-{PORT}"
START_TIME = time.time()

processed_count = 0
lock = threading.Lock()


# ---------- Task handlers ----------
def t_sum(data):
    return sum(float(x) for x in data)

def t_factorial(data):
    n = int(data)
    if n < 0 or n > 500:
        raise ValueError("n must be between 0 and 500")
    return math.factorial(n)

def t_fibonacci(data):
    n = int(data)
    if n < 0 or n > 5000:
        raise ValueError("n must be between 0 and 5000")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

def t_prime(data):
    n = int(data)
    if n < 2:
        return False
    for i in range(2, int(math.isqrt(n)) + 1):
        if n % i == 0:
            return False
    return True

def t_reverse(data):
    return str(data)[::-1]

def t_upper(data):
    return str(data).upper()

def t_wordcount(data):
    return len(str(data).split())


HANDLERS = {
    "sum": t_sum,
    "factorial": t_factorial,
    "fibonacci": t_fibonacci,
    "prime": t_prime,
    "reverse": t_reverse,
    "upper": t_upper,
    "wordcount": t_wordcount,
}


# ---------- Routes ----------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "worker": WORKER_ID,
        "status": "up",
        "processed": processed_count,
        "uptime_sec": round(time.time() - START_TIME, 1),
    })


@app.route("/execute", methods=["POST"])
def execute():
    global processed_count
    body = request.get_json(silent=True) or {}
    task = body.get("task")
    data = body.get("data")

    if task not in HANDLERS:
        return jsonify({"error": f"Unknown task '{task}'",
                        "supported": list(HANDLERS)}), 400
    try:
        time.sleep(0.3)  # processing time simulate karne ke liye
        result = HANDLERS[task](data)
    except Exception as e:
        return jsonify({"error": str(e), "worker": WORKER_ID}), 422

    with lock:
        processed_count += 1
    print(f"[{WORKER_ID}] task={task} data={str(data)[:40]} -> {str(result)[:40]}")
    return jsonify({"worker": WORKER_ID, "result": result})


if __name__ == "__main__":
    print(f"{WORKER_ID} starting on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
"""
Command-line client.

  python client.py demo                      -> 6 sample tasks
  python client.py submit sum 10,20,30       -> single task
  python client.py submit reverse "hello"
  python client.py workers                   -> worker status
  python client.py history                   -> task history
  python client.py stats                     -> summary
"""
import sys
import json
import requests

LB = "http://127.0.0.1:5000"


def submit(task, data):
    r = requests.post(f"{LB}/submit", json={"task": task, "data": data})
    j = r.json()
    if j["status"] == "completed":
        print(f"#{j['task_id']:<3} {task:<10} -> {str(j['result'])[:40]:<20} "
              f"by {j['handled_by']}  ({j['time_ms']} ms, "
              f"{len(j['attempts'])} attempt(s))")
    else:
        print(f"#{j['task_id']:<3} {task:<10} FAILED: {j.get('error')}")


def parse_data(task, raw):
    if task == "sum":
        return [float(x) for x in raw.split(",")]
    if task in ("factorial", "fibonacci", "prime"):
        return int(raw)
    return raw


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]

    if cmd == "demo":
        samples = [
            ("sum", [10, 20, 30]),
            ("factorial", 10),
            ("prime", 97),
            ("reverse", "distributed"),
            ("wordcount", "load balancing makes systems scalable"),
            ("fibonacci", 30),
        ]
        for t, d in samples:
            submit(t, d)
    elif cmd == "submit" and len(sys.argv) >= 4:
        submit(sys.argv[2], parse_data(sys.argv[2], sys.argv[3]))
    elif cmd in ("workers", "history", "stats"):
        print(json.dumps(requests.get(f"{LB}/{cmd}").json(), indent=2))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
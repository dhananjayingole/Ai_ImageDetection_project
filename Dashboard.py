"""
Streamlit dashboard for the Distributed Task Management System.

Run (load balancer + workers pehle se chalu hone chahiye):
    streamlit run dashboard.py
"""
import random
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Distributed Task System", page_icon="🖧",
                   layout="wide")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Settings")
    LB = st.text_input("Load balancer URL", "http://127.0.0.1:5000").rstrip("/")
    auto = st.toggle("Auto-refresh monitoring (3 sec)", value=True)
    st.divider()
    st.caption(
        "**Architecture**\n\n"
        "Streamlit UI → Load Balancer (:5000) → Workers (:5001, :5002, :5003)\n\n"
        "Algorithm: Round Robin + failover + health checks"
    )


# ---------------- Helpers ----------------
def api_get(path):
    try:
        r = requests.get(f"{LB}{path}", timeout=3)
        return r.json()
    except requests.RequestException:
        return None


def api_post(task, data):
    try:
        r = requests.post(f"{LB}/submit", json={"task": task, "data": data},
                          timeout=15)
        return r.json()
    except requests.RequestException as e:
        return {"status": "failed", "error": f"Load balancer unreachable: {e}"}


TASKS = {
    "sum": ("10,20,30", "Comma-separated numbers"),
    "factorial": ("10", "Integer 0-500"),
    "fibonacci": ("30", "Integer 0-5000"),
    "prime": ("97", "Integer"),
    "reverse": ("distributed", "Any text"),
    "upper": ("distributed computing", "Any text"),
    "wordcount": ("load balancing makes systems scalable", "Any text"),
}


def parse(task, raw):
    if task == "sum":
        return [float(x) for x in raw.split(",") if x.strip()]
    if task in ("factorial", "fibonacci", "prime"):
        return int(raw)
    return raw


def random_task():
    task = random.choice(list(TASKS))
    if task == "sum":
        return task, [random.randint(1, 100) for _ in range(5)]
    if task == "factorial":
        return task, random.randint(1, 30)
    if task == "fibonacci":
        return task, random.randint(10, 200)
    if task == "prime":
        return task, random.randint(2, 10000)
    return task, random.choice(["hello world", "distributed systems",
                                "round robin load balancer"])


# ---------------- Header ----------------
st.title("🖧 Distributed Task Management System")
st.caption("Load Balancing · Fault Tolerance · Health Monitoring")

# ---------------- Submit section ----------------
left, right = st.columns([1, 1], gap="large")

with left:
    st.subheader("Submit a task")
    task = st.selectbox("Task type", list(TASKS))
    default, hint = TASKS[task]
    raw = st.text_input("Data", value=default, help=hint, key=f"data_{task}")

    if st.button("Submit task", type="primary"):
        try:
            res = api_post(task, parse(task, raw))
            st.session_state["last_result"] = res
        except ValueError:
            st.session_state["last_result"] = {
                "status": "failed", "error": f"Invalid data for '{task}'. {hint}"}

    res = st.session_state.get("last_result")
    if res:
        if res.get("status") == "completed":
            st.success(f"Task #{res['task_id']} completed by "
                       f"**{res['handled_by']}** in {res['time_ms']} ms")
            st.metric("Result", str(res["result"]))
            if len(res["attempts"]) > 1:
                st.warning("Failover hua: pehla worker unavailable tha, "
                           "task doosre worker pe gaya.")
            with st.expander("Attempts"):
                st.json(res["attempts"])
        else:
            st.error(res.get("error", "Task failed"))

with right:
    st.subheader("Send multiple tasks (load test)")
    n = st.slider("Number of tasks", 3, 60, 9)
    if st.button("Send burst of tasks"):
        jobs = [random_task() for _ in range(n)]
        with st.spinner(f"Sending {n} tasks concurrently..."):
            with ThreadPoolExecutor(max_workers=10) as ex:
                results = list(ex.map(lambda j: api_post(*j), jobs))
        done = [r for r in results if r.get("status") == "completed"]
        st.success(f"{len(done)}/{n} tasks completed")
        if done:
            dist = pd.Series([r["handled_by"] for r in done]).value_counts()
            st.caption("Tasks per worker in this burst")
            st.bar_chart(dist)
        failed = n - len(done)
        if failed:
            st.error(f"{failed} task(s) failed (workers down?)")

st.divider()


# ---------------- Monitoring (auto-refreshing fragment) ----------------
@st.fragment(run_every=3 if auto else None)
def monitoring():
    st.subheader("Live monitoring")
    stats = api_get("/stats")
    workers = api_get("/workers")
    history = api_get("/history")

    if stats is None or workers is None:
        st.error("Load balancer se connect nahi ho pa raha. "
                 "Pehle `python app.py` chalao.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total submitted", stats["total_submitted"])
    c2.metric("Completed", stats["completed"])
    c3.metric("Failed", stats["failed"])
    c4.metric("Workers alive", f"{stats['workers_alive']} / {stats['workers_total']}")

    wcol, ccol = st.columns([3, 2], gap="large")
    wdf = pd.DataFrame([{
        "Worker": w["url"].replace("http://", ""),
        "Status": "🟢 UP" if w["alive"] else "🔴 DOWN",
        "Tasks handled": w["tasks_handled"],
        "Failures": w["failures"],
        "Last health check": w["last_checked"] or "-",
    } for w in workers])
    with wcol:
        st.markdown("**Worker status**")
        st.dataframe(wdf, hide_index=True)
    with ccol:
        st.markdown("**Load distribution**")
        st.bar_chart(wdf.set_index("Worker")["Tasks handled"])

    st.markdown("**Task history** (latest first)")
    if not history:
        st.info("Abhi tak koi task submit nahi hua.")
        return
    hdf = pd.DataFrame([{
        "ID": h["task_id"],
        "Time": h["timestamp"],
        "Task": h["task"],
        "Data": str(h.get("data"))[:40],
        "Status": "✅ completed" if h["status"] == "completed" else "❌ failed",
        "Handled by": h.get("handled_by", "-"),
        "Result": str(h.get("result", h.get("error", "")))[:40],
        "ms": h.get("time_ms", "-"),
        "Attempts": len(h["attempts"]),
        "Failover": "yes" if len(h["attempts"]) > 1 else "",
    } for h in reversed(history)])
    st.dataframe(hdf, hide_index=True)


monitoring()
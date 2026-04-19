import uuid
import time
import random
import threading
import queue
import json
from datetime import datetime
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

# ── In-memory stores ──────────────────────────────────────────────────────────
tasks_store = {}
event_queues = {}

# ── Resource Ledger (simulated global pool) ───────────────────────────────────
INITIAL_RESOURCES = {"cpu": 100, "memory": 100, "api_tokens": 100}
resource_ledger = dict(INITIAL_RESOURCES)
ledger_lock = threading.Lock()

# ── Agent definitions ─────────────────────────────────────────────────────────
AGENT_PROFILES = [
    {
        "name": "Parser Agent",
        "role": "Parse & Validate Input",
        "icon": "⚙️",
        "result_template": "Input parsed successfully. Extracted schema with {n} fields. All constraints validated.",
    },
    {
        "name": "Analyzer Agent",
        "role": "Analyze Requirements",
        "icon": "🔍",
        "result_template": "Analysis complete. Identified {n} key dependencies and {m} optimization paths.",
    },
    {
        "name": "Executor Agent",
        "role": "Execute Core Logic",
        "icon": "⚡",
        "result_template": "Execution complete. Processed {n} operations in {t}ms with 0 errors.",
    },
    {
        "name": "Validator Agent",
        "role": "Validate Output",
        "icon": "✅",
        "result_template": "Validation passed. {n}/{n} assertions satisfied. Confidence: {c}%.",
    },
    {
        "name": "Summarizer Agent",
        "role": "Summarize Results",
        "icon": "📋",
        "result_template": "Summary generated. Aggregated outputs from {n} upstream agents into final response.",
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def emit(task_id, event_type, data):
    if task_id in event_queues:
        event_queues[task_id].put(
            {"type": event_type, "data": data, "ts": datetime.now().isoformat()}
        )


def emit_ledger(task_id):
    with ledger_lock:
        snapshot = dict(resource_ledger)
    emit(task_id, "ledger_update", snapshot)


def fmt_result(template):
    return template.format(
        n=random.randint(3, 12),
        m=random.randint(2, 5),
        t=random.randint(120, 900),
        c=random.randint(94, 99),
    )


# ── Agent runner ──────────────────────────────────────────────────────────────
def run_agent(task_id, subtask, result_store):
    cid = f"ctr-{subtask['id'][:6]}"
    agent = subtask["agent"]
    priority = subtask["priority"]

    # 1. Bid for resources
    emit(task_id, "resource_bid", {"agent": agent, "cid": cid, "priority": priority, "requesting": {"cpu": 20, "memory": 20}})
    time.sleep(0.4)

    # 2. Acquire resources (priority-weighted: higher priority waits less)
    wait = max(0.1, (10 - priority) * 0.1)
    time.sleep(wait)
    with ledger_lock:
        resource_ledger["cpu"] = max(0, resource_ledger["cpu"] - 20)
        resource_ledger["memory"] = max(0, resource_ledger["memory"] - 20)
        resource_ledger["api_tokens"] = max(0, resource_ledger["api_tokens"] - 5)
    emit(task_id, "resource_granted", {"agent": agent, "cid": cid, "priority": priority})
    emit_ledger(task_id)
    time.sleep(0.2)

    # 3. Spin up container
    emit(task_id, "container_start", {"agent": agent, "cid": cid, "status": "STARTING"})
    time.sleep(random.uniform(0.3, 0.6))
    emit(task_id, "container_ready", {"agent": agent, "cid": cid, "status": "RUNNING"})

    # 4. Execute
    emit(task_id, "agent_executing", {"agent": agent, "cid": cid, "task": subtask["role"]})
    time.sleep(random.uniform(1.0, 2.2))

    # 5. Complete
    result = fmt_result(subtask["result_template"])
    emit(task_id, "agent_complete", {"agent": agent, "cid": cid, "result": result, "status": "SUCCESS"})
    result_store[agent] = result
    time.sleep(0.2)

    # 6. Tear down container, release resources
    emit(task_id, "container_terminated", {"agent": agent, "cid": cid})
    with ledger_lock:
        resource_ledger["cpu"] = min(100, resource_ledger["cpu"] + 20)
        resource_ledger["memory"] = min(100, resource_ledger["memory"] + 20)
        resource_ledger["api_tokens"] = min(100, resource_ledger["api_tokens"] + 5)
    emit_ledger(task_id)


# ── Orchestrator ──────────────────────────────────────────────────────────────
def orchestrate(task_id, description):
    tasks_store[task_id]["status"] = "running"

    emit(task_id, "orch", {"msg": f'Received task: "{description}"', "phase": "INIT"})
    time.sleep(0.6)

    # Decompose into subtasks
    emit(task_id, "orch", {"msg": "Decomposing task into subtasks…", "phase": "DECOMPOSE"})
    subtasks = []
    for profile in AGENT_PROFILES:
        subtasks.append(
            {
                "id": str(uuid.uuid4()),
                "agent": profile["name"],
                "role": profile["role"],
                "result_template": profile["result_template"],
                "priority": random.randint(4, 10),
            }
        )
    time.sleep(0.5)
    emit(task_id, "decomposed", {"subtasks": [{"agent": s["agent"], "role": s["role"], "priority": s["priority"]} for s in subtasks]})
    tasks_store[task_id]["subtasks"] = subtasks
    time.sleep(0.4)

    # Sort by priority
    subtasks.sort(key=lambda x: x["priority"], reverse=True)
    emit(task_id, "orch", {"msg": f"Scheduling {len(subtasks)} agents by priority score…", "phase": "SCHEDULE"})
    time.sleep(0.4)

    # Run in two parallel batches
    result_store = {}
    for batch in [subtasks[:2], subtasks[2:4], subtasks[4:]]:
        threads = [threading.Thread(target=run_agent, args=(task_id, s, result_store)) for s in batch]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        time.sleep(0.2)

    # Aggregate
    emit(task_id, "orch", {"msg": "All agents finished. Aggregating results…", "phase": "AGGREGATE"})
    time.sleep(0.6)

    tasks_store[task_id]["status"] = "completed"
    tasks_store[task_id]["result"] = result_store
    emit(task_id, "done", {"results": result_store, "agents": len(subtasks)})

    # Signal end of SSE stream
    event_queues[task_id].put(None)


# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/submit", methods=["POST"])
def submit():
    body = request.json or {}
    description = body.get("task", "").strip() or "Run a generic AI workflow"

    task_id = str(uuid.uuid4())[:12]
    tasks_store[task_id] = {"id": task_id, "task": description, "status": "pending", "created_at": datetime.now().isoformat()}
    event_queues[task_id] = queue.Queue()

    t = threading.Thread(target=orchestrate, args=(task_id, description), daemon=True)
    t.start()

    return jsonify({"task_id": task_id})


@app.route("/api/stream/<task_id>")
def stream(task_id):
    if task_id not in event_queues:
        return jsonify({"error": "Not found"}), 404

    def generate():
        while True:
            ev = event_queues[task_id].get()
            if ev is None:
                yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                break
            yield f"data: {json.dumps(ev)}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/ledger")
def ledger():
    with ledger_lock:
        return jsonify(dict(resource_ledger))


if __name__ == "__main__":
    app.run(debug=True, port=5000, threaded=True)

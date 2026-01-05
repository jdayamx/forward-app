from flask import Flask, request, jsonify
import subprocess
import socket
import time
import threading
import os
import signal
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

TTL_SECONDS = 30 * 60
CLEAN_INTERVAL = 10

forwards = {}


def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("0.0.0.0", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def kill_process(proc: subprocess.Popen):
    try:
        proc.terminate()
        proc.wait(timeout=3)
    except:
        try:
            os.kill(proc.pid, signal.SIGKILL)
        except:
            pass


def cleaner_loop():
    while True:
        now = datetime.utcnow()
        to_delete = []

        for fid, data in forwards.items():
            proc = data["process"]
            started = data["started_at"]

            # 1) процес вже мертвий
            if proc.poll() is not None:
                to_delete.append(fid)
                continue

            # 2) TTL
            if (now - started).total_seconds() >= TTL_SECONDS:
                kill_process(proc)
                to_delete.append(fid)

        for fid in to_delete:
            forwards.pop(fid, None)

        time.sleep(CLEAN_INTERVAL)


@app.route("/open", methods=["POST"])
def open_forward():
    local_port = request.json.get("port")
    if not local_port:
        return jsonify({"error": "port required"}), 400

    public_port = find_free_port()
    fid = str(uuid.uuid4())

    cmd = [
        "socat",
        f"TCP-LISTEN:{public_port},reuseaddr,fork",
        f"TCP:127.0.0.1:{local_port}"
    ]

    proc = subprocess.Popen(cmd)

    forwards[fid] = {
        "local_port": local_port,
        "public_port": public_port,
        "process": proc,
        "started_at": datetime.utcnow()
    }

    return jsonify({
        "id": fid,
        "local_port": local_port,
        "public_port": public_port,
        "ttl_minutes": 30
    })


@app.route("/close", methods=["POST"])
def close_forward():
    fid = request.json.get("id")
    if fid not in forwards:
        return jsonify({"error": "not found"}), 404

    kill_process(forwards[fid]["process"])
    forwards.pop(fid)

    return jsonify({"status": "closed"})


@app.route("/list", methods=["GET"])
def list_forwards():
    now = datetime.utcnow()
    result = []

    for fid, data in forwards.items():
        result.append({
            "id": fid,
            "local_port": data["local_port"],
            "public_port": data["public_port"],
            "pid": data["process"].pid,
            "uptime_sec": int((now - data["started_at"]).total_seconds())
        })

    return jsonify(result)

@app.route("/")
def index():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Socat Port Forwarding API</title>
    <style>
        body {
            font-family: system-ui, sans-serif;
            padding: 2rem;
            background: #fdfdfd;
            color: #222;
        }
        h1 { color: #333; }
        h2 { margin-top: 2rem; color: #444; }
        pre {
            background: #f4f4f4;
            padding: 1rem;
            border-left: 4px solid #ccc;
            overflow-x: auto;
        }
        code {
            background: #eee;
            padding: 2px 6px;
            border-radius: 4px;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 1rem;
        }
        th, td {
            border: 1px solid #ccc;
            padding: 0.6rem 1rem;
            text-align: left;
        }
        th {
            background: #eee;
        }
        tr:nth-child(even) {
            background: #f9f9f9;
        }
        .note {
            background: #fff8e1;
            padding: 1rem;
            border-left: 4px solid #ffcc00;
            margin-top: 1rem;
        }
    </style>
</head>
<body>

<h1>🔀 Socat Port Forwarding API</h1>

<p>
Цей сервіс дозволяє тимчасово відкривати TCP-форварди за допомогою
<code>socat</code>.
Публічний порт обирається автоматично, а кожен форвард має обмежений час життя.
</p>

<div class="note">
<b>⏱ TTL:</b> кожен форвард автоматично завершується через <b>30 хвилин</b>,
навіть якщо процес ще живий.
</div>

<h2>🚀 POST <code>/open</code></h2>
<p>
Створює TCP-форвард з випадкового вільного <b>public_port</b> → <b>local_port</b>.
</p>

<h3>Request</h3>
<pre>{
  "port": 8080
}</pre>

<h3>Response</h3>
<pre>{
  "id": "c2c44b4e-0c8a-4c7c-9b33-5d2f88c3b7fa",
  "local_port": 8080,
  "public_port": 49152,
  "ttl_minutes": 30
}</pre>

<h2>🛑 POST <code>/close</code></h2>
<p>
Примусово завершує форвард за його <code>id</code>.
</p>

<h3>Request</h3>
<pre>{
  "id": "c2c44b4e-0c8a-4c7c-9b33-5d2f88c3b7fa"
}</pre>

<h3>Response</h3>
<pre>{
  "status": "closed"
}</pre>

<h2>📋 GET <code>/list</code></h2>
<p>
Повертає список усіх активних форвардів.
</p>

<h3>Response</h3>
<pre>[
  {
    "id": "c2c44b4e-0c8a-4c7c-9b33-5d2f88c3b7fa",
    "local_port": 8080,
    "public_port": 49152,
    "pid": 12345,
    "uptime_sec": 412
  }
]</pre>

<h2>📌 Notes</h2>
<ul>
    <li><b>public_port</b> обирається автоматично ОС.</li>
    <li>Форвард існує не більше <b>30 хвилин</b>.</li>
    <li>Після завершення TTL процес <code>socat</code> жорстко прибивається.</li>
    <li>Після рестарту Flask-сервісу всі форварди втрачаються.</li>
</ul>

</body>
</html>
"""

if __name__ == "__main__":
    threading.Thread(target=cleaner_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=3003)

from flask import Flask, request, jsonify
import subprocess
import socket

app = Flask(__name__)

socat_processes = {}

def find_free_port(start_port):
    port = start_port + 1
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('0.0.0.0', port)) != 0:
                return port
        port += 1

def is_port_alive(port):
    """Перевірка чи порт LISTEN."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("0.0.0.0", port)) == 0
    
def cleanup_dead_forwards():
    """Перевіряє всі socat процеси, і якщо якийсь не відповідає — прибиває."""
    global socat_processes

    ports_to_delete = []

    for local_port, proc in socat_processes.items():
        public_port = local_port + 1

        # 1) Перевірка чи процес живий
        if proc.poll() is not None:
            ports_to_delete.append(local_port)
            continue

        # 2) Перевірка чи порт реально слухає
        if not is_port_alive(public_port):
            try:
                proc.terminate()
            except:
                pass
            ports_to_delete.append(local_port)

    # Прибираємо мертві з dict
    for p in ports_to_delete:
        del socat_processes[p]

@app.route('/open', methods=['GET'])
def open_port():
    global socat_processes

    # 🔥 ПЕРЕД open — ПОВНА ПЕРЕВІРКА ВСІХ ПРОЦЕСІВ
    cleanup_dead_forwards()

    port = request.args.get('port', type=int)
    if not port:
        return jsonify({"status": "error", "message": "Port can not be empty"}), 400
    if port not in socat_processes:
        public_port = find_free_port(port)
        SOCAT_CMD = ["socat", f"TCP-LISTEN:{public_port},reuseaddr,fork", f"TCP:0.0.0.0:{port}"]
        socat_processes[port] = subprocess.Popen(SOCAT_CMD)
        return jsonify({"status": "success", "local_port": port, "public_port": public_port}), 200
    return jsonify({"status": "error", "message": f"Port {port} already forwarded to {port + 1}"}), 400

@app.route('/close', methods=['GET'])
def close_port():
    global socat_processes
    port = request.args.get('port', type=int)
    if not port:
        return jsonify({"status": "error", "message": "Port can not be empty"}), 400
    if port in socat_processes:
        socat_processes[port].terminate()
        del socat_processes[port]
        return jsonify({"status": "success", "message": f"Forward {port} to {port + 1} is closed"}), 200
    return jsonify({"status": "error", "message": "Port already closed"}), 400

@app.route('/list', methods=['GET'])
def list_ports():
    global socat_processes
    return jsonify([
        {
            "local_port": port,
            "public_port": port + 1,
            "pid": proc.pid
        }
        for port, proc in socat_processes.items()
    ]), 200

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Socat Forwarding API</title>
        <style>
            body { font-family: sans-serif; padding: 2rem; background: #fdfdfd; color: #222; }
            h1 { color: #444; }
            h2 { margin-top: 2rem; color: #555; }
            pre { background: #f4f4f4; padding: 1rem; border-left: 3px solid #ccc; overflow-x: auto; }
            code { background: #eee; padding: 2px 4px; border-radius: 4px; }
            table { border-collapse: collapse; width: 100%; margin-top: 1rem; }
            th, td { border: 1px solid #ccc; padding: 0.5rem 1rem; text-align: left; }
            th { background: #eee; }
            tr:nth-child(even) { background: #f9f9f9; }
        </style>
    </head>
    <body>
        <h1>Socat Forwarding API</h1>
        <p>This API allows you to create temporary TCP proxies using <code>socat</code>.</p>

        <h2>🚀 <code>GET /open?port=PORT</code></h2>
        <p>Creates a proxy from <code>PORT + 1 → PORT</code>.</p>
        <h3>Example</h3>
        <pre>GET /open?port=8080</pre>
        <h3>Response</h3>
        <pre>{
  "status": "success",
  "local_port": 8080,
  "public_port": 8081
}</pre>
        <h3>If the port is already open</h3>
        <pre>{
  "status": "error",
  "message": "Port 8080 already forwarded to 8081"
}</pre>

        <h2>🛑 <code>GET /close?port=PORT</code></h2>
        <p>Terminates the proxy from <code>PORT + 1 → PORT</code>.</p>
        <h3>Example</h3>
        <pre>GET /close?port=8080</pre>
        <h3>Response</h3>
        <pre>{
  "status": "success",
  "message": "Forward 8080 to 8081 is closed"
}</pre>
        <h3>If the forwarding is already closed</h3>
        <pre>{
  "status": "error",
  "message": "Port already closed"
}</pre>

        <h2>📋 <code>GET /list</code></h2>
        <p>Displays all active proxy connections.</p>
        <h3>Example</h3>
        <pre>GET /list</pre>
        <h3>Response</h3>
        <pre>[
  {
    "local_port": 8080,
    "public_port": 8081,
    "pid": 12345
  },
  {
    "local_port": 3000,
    "public_port": 3001,
    "pid": 12346
  }
]</pre>

        <h2>📌 Notes</h2>
        <ul>
            <li>All requests are <code>GET</code> requests.</li>
            <li><code>local_port</code> is the port where traffic is forwarded to.</li>
            <li><code>public_port</code> is the open port for external connections.</li>
            <li>After restarting the Flask app, forwarding needs to be recreated.</li>
        </ul>
    </body>
    </html>
    """


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3003)
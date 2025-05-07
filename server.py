from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

socat_process = None  # Тут зберігаємо процес `socat`

@app.route('/open', methods=['GET'])
def open_port():
    global socat_process
    port = request.args.get('port', type=int)  # Отримуємо порт з параметрів запиту
    if not port:
        return jsonify({"status": "error", "message": "Не вказано порт"}), 400
    if socat_process is None:
        # Змінюємо команду для динамічного використання порту
        SOCAT_CMD = ["socat", f"TCP-LISTEN:3004,reuseaddr,fork", f"TCP:0.0.0.0:{port}"]
        socat_process = subprocess.Popen(SOCAT_CMD)
        return jsonify({"status": "success", "message": f"Порт {port} відкрито"}), 200
    return jsonify({"status": "error", "message": "Порт вже відкритий"}), 400

@app.route('/close', methods=['GET'])
def close_port():
    global socat_process
    port = request.args.get('port', type=int)  # Отримуємо порт з параметрів запиту
    if not port:
        return jsonify({"status": "error", "message": "Не вказано порт"}), 400
    if socat_process is not None:
        socat_process.terminate()  # Завершуємо процес
        socat_process = None
        return jsonify({"status": "success", "message": f"Порт {port} закрито"}), 200
    return jsonify({"status": "error", "message": "Порт вже закритий"}), 400

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3003)
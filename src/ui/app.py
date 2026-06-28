from flask import Flask, jsonify, render_template
import json
import os

app = Flask(__name__)
STATUS_FILE = "/usr/local/share/lp_to_denon/lp_status.json"

def get_current_status():
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading status file: {e}")
    
    # Default status
    return {
        "status": "searching",
        "device_name": None,
        "device_address": None
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    return jsonify(get_current_status())

if __name__ == "__main__":
    # Host on 0.0.0.0 so the user can also view the status from their phone/PC in the local network!
    app.run(host="0.0.0.0", port=5000)

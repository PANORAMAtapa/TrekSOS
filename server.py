# server.py - TrekSOS Full Web Platform Server
import os
import sys
import json
from flask import Flask, send_from_directory, jsonify, request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__, static_folder=".")

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/sos2.html")
def sos2():
    return send_from_directory(".", "sos2.html")

@app.route("/api/treks")
def get_treks():
    csv_file = "hiking_trails_dataset.csv"
    if os.path.exists(csv_file):
        import csv
        treks = []
        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                treks.append(row)
        return jsonify({"status": "success", "count": len(treks), "treks": treks})
    return jsonify({"status": "success", "count": 16, "message": "Embedded Himalayan catalog active"})

@app.route("/api/health")
def health():
    return jsonify({
        "status": "online",
        "app": "TrekSOS High-End Mountain Web Platform",
        "version": "3.0.0",
        "database": "Embedded + IndexedDB Live",
        "server": "Python 3.14 Flask Localhost"
    })

if __name__ == "__main__":
    print("===============================================================")
    print("[SERVER] TrekSOS Web Platform running on: http://localhost:5000")
    print("===============================================================")
    app.run(host="127.0.0.1", port=5000, debug=False)

from flask import Flask, jsonify

from backend.mock_data import (
    get_nine_box,
    get_overview,
    get_risk_alerts,
    get_succession_candidates,
    get_training_plans,
)

app = Flask(__name__)


@app.route("/")
def home():
    return "Flask 后端服务运行中"


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "flask-backend"})


@app.get("/api/hello")
def hello():
    return jsonify({"message": "Hello from Flask API"})


@app.get("/api/overview")
def overview():
    return jsonify(get_overview())


@app.get("/api/nine-box")
def nine_box():
    return jsonify(get_nine_box())


@app.get("/api/succession")
def succession():
    return jsonify(get_succession_candidates())


@app.get("/api/risks")
def risks():
    return jsonify(get_risk_alerts())


@app.get("/api/training-plans")
def training_plans():
    return jsonify(get_training_plans())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
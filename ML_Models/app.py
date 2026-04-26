import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request

import stockdata
from ensemble_inference import (
    RuntimeConfigurationError,
    bootstrap_state,
    get_portfolio,
    get_status,
    get_today_recommendations,
    read_state,
    run_day,
    simulate_from_request,
)

load_dotenv()

app = Flask(__name__)


def verified_request():
    return request.headers.get("Token") == os.getenv("SERVER_SECRET")


def require_token():
    if not verified_request():
        return jsonify({"message": "invalid request"}), 401
    return None


def runtime_error_response(exc):
    code = 503 if isinstance(exc, RuntimeConfigurationError) else 500
    return jsonify({"message": str(exc)}), code


@app.route("/")
def hello():
    return "AlgoFlux Ensemble Inference Service"


@app.route("/ping")
def yo():
    return "pong"

@app.route("/model", methods=["POST"])
def predict():
    auth_error = require_token()
    if auth_error:
        return auth_error
    return jsonify(
        {
            "message": "Legacy /model prediction route is disabled. Use the /ensemble endpoints for the inference-only trading workflow."
        }
    ), 410


@app.route("/search", methods=["POST"])
def search():
    company = request.get_json()["company"]
    return jsonify(stockdata.stock_data(company))


@app.route("/ensemble/status", methods=["POST"])
def ensemble_status():
    auth_error = require_token()
    if auth_error:
        return auth_error
    try:
        return jsonify(get_status())
    except Exception as exc:
        return runtime_error_response(exc)


@app.route("/ensemble/recommendations", methods=["POST"])
def ensemble_recommendations():
    auth_error = require_token()
    if auth_error:
        return auth_error
    try:
        state = read_state()
        return jsonify(get_today_recommendations(state))
    except Exception as exc:
        return runtime_error_response(exc)


@app.route("/ensemble/portfolio", methods=["POST"])
def ensemble_portfolio():
    auth_error = require_token()
    if auth_error:
        return auth_error
    try:
        return jsonify(get_portfolio())
    except Exception as exc:
        return runtime_error_response(exc)


@app.route("/ensemble/simulate", methods=["POST"])
def ensemble_simulate():
    auth_error = require_token()
    if auth_error:
        return auth_error
    try:
        body = request.get_json() or {}
        trades = body.get("trades", [])
        initial_capital = body.get("initialCapital", 1000000)
        return jsonify(simulate_from_request(trades, initial_capital))
    except Exception as exc:
        return runtime_error_response(exc)


@app.route("/ensemble/run-day", methods=["POST"])
def ensemble_run_day():
    auth_error = require_token()
    if auth_error:
        return auth_error
    try:
        return jsonify(run_day())
    except Exception as exc:
        return runtime_error_response(exc)


@app.route("/ensemble/bootstrap", methods=["POST"])
def ensemble_bootstrap():
    auth_error = require_token()
    if auth_error:
        return auth_error
    try:
        return jsonify(bootstrap_state(force=bool((request.get_json() or {}).get("force"))))
    except Exception as exc:
        return runtime_error_response(exc)


if __name__ == "__main__":
    app.run(debug=True, port=6969)

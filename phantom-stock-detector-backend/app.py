"""Minimal Flask JSON API for the separately built frontend."""
import json
from pathlib import Path
import pandas as pd
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"

def _read_csv(name):
    """Read a generated output CSV or return None when the pipeline has not run."""
    path = OUTPUT_DIR / name
    if not path.exists():
        return None
    try:
        return pd.read_csv(path, dtype={"store_id": str, "sku_id": str})
    except (OSError, pd.errors.ParserError):
        return None

def _json_records(frame):
    """Convert a DataFrame to JSON-safe records."""
    if frame is None or frame.empty:
        return []
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")

def _pipeline_error():
    return jsonify({"error": "Pipeline outputs are not available. Run: python run_pipeline.py --schema config/schema.demo.json"}), 503

@app.get("/")
def index():
    return jsonify({
        "project": "Phantom Stock-Out Detector",
        "status": "running",
        "message": "Use /api/health, /api/dates, /api/stores, /api/alerts, and /api/history."
    })

@app.get("/api/health")
def health():
    alerts, history = _read_csv("daily_alerts.csv"), _read_csv("alert_history.csv")
    return jsonify({
        "status": "ok" if alerts is not None and history is not None else "needs_pipeline",
        "daily_alerts_available": alerts is not None,
        "alert_history_available": history is not None,
        "daily_alert_rows": 0 if alerts is None else len(alerts),
        "history_rows": 0 if history is None else len(history),
    })

@app.get("/api/dates")
def dates():
    alerts = _read_csv("daily_alerts.csv")
    if alerts is None:
        return _pipeline_error()
    return jsonify(sorted(alerts["date"].dropna().astype(str).unique().tolist()))

@app.get("/api/stores")
def stores():
    alerts = _read_csv("daily_alerts.csv")
    if alerts is None:
        return _pipeline_error()
    date = request.args.get("date")
    if date:
        try:
            pd.to_datetime(date, format="%Y-%m-%d", errors="raise")
        except ValueError:
            return jsonify({"error": "date must use YYYY-MM-DD format"}), 400
        alerts = alerts[alerts["date"].astype(str) == date]
    return jsonify(sorted(alerts["store_id"].dropna().astype(str).unique().tolist()))

@app.get("/api/alerts")
def alerts():
    date, store_id = request.args.get("date"), request.args.get("store_id")
    if not date or not store_id:
        return jsonify({"error": "Both date=YYYY-MM-DD and store_id are required."}), 400
    try:
        pd.to_datetime(date, format="%Y-%m-%d", errors="raise")
    except ValueError:
        return jsonify({"error": "date must use YYYY-MM-DD format"}), 400
    frame = _read_csv("daily_alerts.csv")
    if frame is None:
        return _pipeline_error()
    selected = frame[(frame["date"].astype(str) == date) & (frame["store_id"].astype(str) == store_id)]
    if not selected.empty:
        selected = selected.sort_values("rank_in_store")
    return jsonify(_json_records(selected))

@app.get("/api/history")
def history():
    store_id, sku_id = request.args.get("store_id"), request.args.get("sku_id")
    if not store_id or not sku_id:
        return jsonify({"error": "Both store_id and sku_id are required."}), 400
    frame = _read_csv("alert_history.csv")
    if frame is None:
        return _pipeline_error()
    selected = frame[(frame["store_id"].astype(str) == store_id) & (frame["sku_id"].astype(str) == sku_id)].copy()
    for param, comparison in [("start_date", "start"), ("end_date", "end")]:
        value = request.args.get(param)
        if value:
            try:
                pd.to_datetime(value, format="%Y-%m-%d", errors="raise")
            except ValueError:
                return jsonify({"error": f"{param} must use YYYY-MM-DD format"}), 400
            if comparison == "start":
                selected = selected[selected["date"].astype(str) >= value]
            else:
                selected = selected[selected["date"].astype(str) <= value]
    return jsonify(_json_records(selected.sort_values("date")))

@app.get("/api/summary")
def summary():
    path = OUTPUT_DIR / "summary_metrics.json"
    if not path.exists():
        return _pipeline_error()
    try:
        return jsonify(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return jsonify({"error": "summary_metrics.json could not be read."}), 500

@app.get("/api/recovery-estimate")
def recovery_estimate():
    path = OUTPUT_DIR / "recovery_estimate.json"
    if not path.exists():
        return _pipeline_error()
    try:
        return jsonify(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return jsonify({"error": "recovery_estimate.json could not be read."}), 500

@app.get("/download/daily-alerts")
def download_alerts():
    path = OUTPUT_DIR / "daily_alerts.csv"
    if not path.exists():
        return _pipeline_error()
    return send_file(path, as_attachment=True, download_name="daily_alerts.csv", mimetype="text/csv")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

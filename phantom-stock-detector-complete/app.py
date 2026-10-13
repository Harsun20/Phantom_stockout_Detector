"""Flask dashboard and JSON API for Phantom Stock-Out Detector."""
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, request, send_file, render_template

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/static",
)


def _missing_file(path):
    return jsonify({
        "error": "Pipeline output is not available yet.",
        "detail": f"Missing {path.name}. Run: python generate_demo_data.py, then python run_pipeline.py --schema config/schema.demo.json --evaluate",
    }), 503


def read_csv_safe(filename):
    path = OUTPUT_DIR / filename
    if not path.exists():
        return None, _missing_file(path)
    try:
        return pd.read_csv(path), None
    except Exception as exc:
        return None, (jsonify({"error": f"Could not read {path.name}.", "detail": str(exc)}), 500)


def read_json_safe(filename):
    path = OUTPUT_DIR / filename
    if not path.exists():
        return None, _missing_file(path)
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, (jsonify({"error": f"Could not read {path.name}.", "detail": str(exc)}), 500)


def json_records(df):
    # Convert pandas missing values and NumPy scalar values to JSON-safe values.
    clean = df.astype(object).where(pd.notna(df), None)
    return json.loads(clean.to_json(orient="records", date_format="iso"))


def valid_date(value, label="date"):
    try:
        pd.to_datetime(value, format="%Y-%m-%d", errors="raise")
        return True
    except (ValueError, TypeError):
        return False


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/api/health")
def health():
    alerts, error = read_csv_safe("daily_alerts.csv")
    if error:
        return error
    history, error = read_csv_safe("alert_history.csv")
    if error:
        return error
    return jsonify({"status": "healthy", "daily_alerts_available": True,
                    "history_available": True, "daily_alert_rows": int(len(alerts)),
                    "history_rows": int(len(history))})


@app.get("/api/dates")
def dates():
    alerts, error = read_csv_safe("daily_alerts.csv")
    if error:
        return error
    return jsonify(sorted(alerts["date"].dropna().astype(str).unique().tolist()) if "date" in alerts else [])


@app.get("/api/stores")
def stores():
    alerts, error = read_csv_safe("daily_alerts.csv")
    if error:
        return error
    date_filter = request.args.get("date")
    if date_filter:
        if not valid_date(date_filter):
            return jsonify({"error": "Invalid date. Use YYYY-MM-DD."}), 400
        if "date" in alerts:
            alerts = alerts[alerts["date"].astype(str) == date_filter]
    return jsonify(sorted(alerts["store_id"].dropna().astype(str).unique().tolist()) if "store_id" in alerts else [])


@app.get("/api/alerts")
def alerts():
    date_filter, store_filter = request.args.get("date"), request.args.get("store_id")
    if not date_filter or not store_filter:
        return jsonify({"error": "Both query parameters are required: date=YYYY-MM-DD and store_id=S001."}), 400
    if not valid_date(date_filter):
        return jsonify({"error": "Invalid date. Use YYYY-MM-DD."}), 400
    df, error = read_csv_safe("daily_alerts.csv")
    if error:
        return error
    if not {"date", "store_id"}.issubset(df.columns):
        return jsonify([])
    result = df[(df["date"].astype(str) == date_filter) & (df["store_id"].astype(str) == store_filter)]
    if "rank_in_store" in result.columns:
        result = result.sort_values("rank_in_store")
    return jsonify(json_records(result))


@app.get("/api/history")
def history():
    store_filter, sku_filter = request.args.get("store_id"), request.args.get("sku_id")
    if not store_filter or not sku_filter:
        return jsonify({"error": "Both query parameters are required: store_id=S001 and sku_id=SKU002."}), 400
    start_date, end_date = request.args.get("start_date"), request.args.get("end_date")
    for label, value in (("start_date", start_date), ("end_date", end_date)):
        if value and not valid_date(value, label):
            return jsonify({"error": f"Invalid {label}. Use YYYY-MM-DD."}), 400
    df, error = read_csv_safe("alert_history.csv")
    if error:
        return error
    required = {"store_id", "sku_id", "date"}
    if not required.issubset(df.columns):
        return jsonify([])
    result = df[(df["store_id"].astype(str) == store_filter) & (df["sku_id"].astype(str) == sku_filter)].copy()
    if start_date:
        result = result[result["date"].astype(str) >= start_date]
    if end_date:
        result = result[result["date"].astype(str) <= end_date]
    return jsonify(json_records(result.sort_values("date")))


@app.get("/api/summary")
def summary():
    payload, error = read_json_safe("summary_metrics.json")
    return error if error else jsonify(payload)


@app.get("/api/recovery-estimate")
def recovery_estimate():
    payload, error = read_json_safe("recovery_estimate.json")
    return error if error else jsonify(payload)


@app.post("/api/run-pipeline")
def run_pipeline():
    """Run the demo pipeline locally and return a readable result."""
    command = [sys.executable, str(BASE_DIR / "run_pipeline.py"),
               "--schema", "config/schema.demo.json", "--evaluate"]
    try:
        result = subprocess.run(command, cwd=str(BASE_DIR), capture_output=True,
                                text=True, timeout=180, check=False)
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Pipeline timed out after 180 seconds."}), 504
    if result.returncode != 0:
        return jsonify({"error": "Pipeline failed.", "detail": (result.stderr or result.stdout)[-4000:]}), 500
    return jsonify({"status": "success", "message": "Pipeline completed successfully.",
                    "detail": result.stdout[-4000:]})


@app.get("/download/daily-alerts")
def download_alerts():
    path = OUTPUT_DIR / "daily_alerts.csv"
    if not path.exists():
        return _missing_file(path)
    return send_file(path, as_attachment=True, download_name="daily_alerts.csv", mimetype="text/csv")


if __name__ == "__main__":
    print("Open the dashboard at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)

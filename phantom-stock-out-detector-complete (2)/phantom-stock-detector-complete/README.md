# Phantom Stock-Out Detector — Backend

A beginner-friendly local Python backend that ranks retail SKU/store combinations for physical shelf checks when recorded stock is positive but sales have unexpectedly stopped.

> **Important prototype disclaimer:** This Round-1 prototype uses synthetic data because organizer data has not yet been released. No real-world performance claim is made from the demo.

The backend only recommends physical verification. **It never updates inventory automatically.** It uses CSV files and Pandas; no database, paid API, external API, cloud service, Docker, or machine-learning library is required.

## 1. How it works

```text
  Sales CSV  +  Inventory CSV  +  Optional promo/store/product CSVs
       |                     |
       +----------+----------+
                  v
        Schema mapping (JSON)
                  v
       Validation and cleaning
                  v
      Join sales + inventory rows
                  v
   Historical demand and streak features
                  v
     Explainable 0–100 risk scoring
                  v
   Rank candidates (maximum top 20/store/day)
                  v
   CSV outputs + JSON metrics + Flask API
                  v
       Separate HTML/CSS/JS frontend
```

## 2. Folder structure

```text
phantom-stock-detector-backend/
├── README.md
├── requirements.txt
├── .gitignore
├── app.py
├── templates/
│   └── index.html
├── static/
│   ├── styles.css
│   └── script.js
├── run_pipeline.py
├── generate_demo_data.py
├── inspect_data.py
├── create_zip.py
├── config/
│   ├── schema.example.json
│   └── schema.demo.json
├── data/
│   ├── README.md
│   └── .gitkeep
├── output/
│   ├── README.md
│   └── .gitkeep
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── data_loader.py
│   ├── schema_adapter.py
│   ├── validation.py
│   ├── feature_engineering.py
│   ├── scoring.py
│   ├── explanations.py
│   ├── recovery_estimate.py
│   └── evaluation.py
└── tests/
    ├── __init__.py
    ├── test_schema_adapter.py
    ├── test_features.py
    ├── test_scoring.py
    └── test_pipeline.py
```

## 3. Prerequisites

- Windows 10/11, macOS, or Linux
- Python 3.10 or newer
- VS Code (recommended, not required)
- Internet only for the initial package install; the application itself makes no web requests

Check Python in a terminal:

```bash
python --version
```

On some Windows installations, use `py --version` if `python` is not recognized.

## 4. Install and run on Windows

Open VS Code, choose **File → Open Folder**, and open this project folder. Then choose **Terminal → New Terminal**.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python generate_demo_data.py
python inspect_data.py --schema config/schema.demo.json
python run_pipeline.py --schema config/schema.demo.json --evaluate
python app.py
```

If PowerShell blocks activation, either run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal and activate again, or use Command Prompt:

```bat
.venv\Scripts\activate.bat
```

Keep the Flask terminal running while testing the API. Open `http://127.0.0.1:5000/` in a browser.

## 5. Install and run on macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python generate_demo_data.py
python inspect_data.py --schema config/schema.demo.json
python run_pipeline.py --schema config/schema.demo.json --evaluate
python app.py
```

## 6. What each command does

- `python generate_demo_data.py` creates six deterministic synthetic CSVs (3 stores, 30 SKUs, 90 days).
- `python inspect_data.py --schema config/schema.demo.json` displays each input's shape, columns, types, sample rows, missing values, and date range.
- `python run_pipeline.py --schema config/schema.demo.json --evaluate` validates inputs, calculates features and scores, writes output files, and optionally evaluates against synthetic ground truth.
- `python app.py` starts a local Flask JSON API on `127.0.0.1:5000`.
- `pytest` runs automated tests.
- `python create_zip.py` creates `../phantom-stock-detector-backend.zip`.

## 7. API endpoints

All endpoints return JSON except the CSV download route.

| Method and route | Purpose |
|---|---|
| `GET /` | Opens the dashboard |
| `GET /api/health` | Output availability and row counts |
| `GET /api/dates` | Dates with ranked alerts |
| `GET /api/stores` | Stores with alerts; optional `?date=YYYY-MM-DD` |
| `GET /api/alerts?date=2026-03-01&store_id=S001` | Ranked alerts for a store/date |
| `GET /api/history?store_id=S001&sku_id=SKU002` | Time series; optional `start_date` and `end_date` |
| `GET /api/summary` | Pipeline metrics and thresholds |
| `GET /api/recovery-estimate` | Illustrative scenario estimate |
| `POST /api/run-pipeline` | Run the demo pipeline from the dashboard |
| `GET /download/daily-alerts` | Download ranked alert CSV |

Example URLs (the exact dates with alerts depend on the data):
- `http://127.0.0.1:5000/api/health`
- `http://127.0.0.1:5000/api/alerts?date=2026-03-01&store_id=S001`
- `http://127.0.0.1:5000/api/history?store_id=S001&sku_id=SKU002`

If outputs have not been generated, API routes return a readable error and instructions to run the pipeline first. The API binds to localhost for safe local development. If a frontend runs on another port, configure development proxying or CORS intentionally; this project does not add a permissive CORS dependency by default.

## 8. Output files

- `output/daily_alerts.csv`: ranked daily physical-check list; maximum `--top-k` rows per store/day.
- `output/alert_history.csv`: time-series values for charts.
- `output/summary_metrics.json`: row counts, date range, threshold settings, runtime, and disclaimer.
- `output/recovery_estimate.json`: an illustrative lost-unit/revenue-at-risk scenario, not measured recovery.
- `output/evaluation.json`: created only with `--evaluate`; synthetic-demo evaluation only.

## 9. Score and alert types

The risk score ranges from 0 to 100. Weights and thresholds live in `src/config.py` so a beginner can tune them. Signals include positive recorded stock, zero-sales streak length, historical demand, unchanged inventory, peer-store demand, promotions, and a slow-mover penalty.

A candidate generally needs:
- recorded on-hand inventory greater than zero;
- at least 3 consecutive zero-sales days;
- expected demand of at least 0.50 units/day; and
- not be classified as a slow mover.

Expected demand is based only on earlier sales: the series is shifted by one day before rolling calculations. The default rolling window is 28 days with 7 observations required, with a prior-only expanding mean fallback for early rows.

- `likely_phantom_stockout`: several signals support a physical check.
- `possible_wrong_shelf`: a candidate has ambiguous evidence, such as no peer benchmark or inventory that is not frozen.
- `monitor`: not a current high-priority candidate.

Confidence labels are score bands, not calibrated probabilities. A high score does not prove theft, loss, or a missing item. Every alert includes a short reason using calculated values. Promotions are mentioned only when active.

Peer demand is a leave-one-out average for stores sharing `store_format` and `city_tier`; missing peer values are allowed. `expected_lost_units` is only a proxy: expected daily demand multiplied by zero-sales streak.

## 10. Schema mapping and organizer data

The standard internal schema is:

- Sales: `date`, `store_id`, `sku_id`, `units_sold`
- Inventory: `date`, `store_id`, `sku_id`, `on_hand`
- Optional promotions: `date`, `store_id`, `sku_id`, `promo_active`
- Optional stores: `store_id`, `store_format`, `store_size`, `city_tier`
- Optional products: `sku_id`, `sku_name`, `category`, `selling_price`

The JSON schema maps internal field names to actual CSV column names. For example, `"units_sold": "qty_sold"` means the input file column `qty_sold` will be renamed to the standard field `units_sold`.

When organizer data arrives:
1. Copy the supplied CSVs into `data/` (do not overwrite your only original copy).
2. Copy `config/schema.example.json` to a new file such as `config/schema.organizer.json`.
3. Edit each `file` and mapping value to match exact organizer file/column names.
4. Run `python inspect_data.py --schema config/schema.organizer.json`.
5. Fix missing/invalid dates, negative quantities, and duplicate date-store-SKU rows in a copy of the data.
6. Run `python run_pipeline.py --schema config/schema.organizer.json --verbose`.
7. Confirm the outputs before connecting the frontend.

Required sales and inventory files must exist and have overlapping keys. Promotion, store, product, and ground-truth files are optional. Missing optional files are handled gracefully. CSV is supported; Excel uploads are not implemented.

## 11. Evaluation

`--evaluate` uses `demo_ground_truth.csv` only for evaluation. Ground truth is never passed to feature generation or scoring. The metric is a per-store-date precision@20 estimate (true positives in the returned list divided by 20), averaged across evaluated store/date groups. Since the synthetic data may not produce 20 alerts in every group, this convention should be interpreted carefully and is only for demo comparisons—not a real-world performance claim.

## 12. Tests

After installing requirements:

```bash
pytest
```

The tests cover column mapping, zero-streak reset, same-day leakage prevention, slow-mover filtering, score bounds, top-K ranking, and pipeline output columns.

## 13. Two-minute team demo script

1. **0:00–0:20** — Explain the invisible retail problem: the system says stock exists while shelves may be empty.
2. **0:20–0:40** — Run `python generate_demo_data.py`; explain that data is synthetic because organizer data is not available.
3. **0:40–1:05** — Run the pipeline and open `output/daily_alerts.csv`; point out rank, score, reason, and recommended action.
4. **1:05–1:35** — Start `python app.py` and show `/api/health`, `/api/dates`, and one `/api/alerts` URL.
5. **1:35–2:00** — Explain the top-20 inspection limit, explainable score, synthetic-only evaluation, and that the system never edits inventory automatically.

## 14. GitHub publication notes

- Do not commit `.venv/`, secrets, real confidential data, or large/generated CSV outputs.
- Commit the Python source, `config/`, tests, and README.
- Demo CSVs are generated locally by `python generate_demo_data.py`.
- GitHub stores the code; it does not run the backend by itself.
- The Flask server in this prototype is intended for local development, not production deployment.

## 15. Costs and limitations

No paid APIs or external APIs are used. No database or machine-learning library is required. Synthetic patterns are simplified and cannot represent all retail behavior. Holidays, returns, stock transfers, data latency, shelf replenishment schedules, and item substitutions may affect alerts. The score is a transparent heuristic, not a trained or calibrated probability. Always physically verify before making inventory adjustments.


## Integrated dashboard

This ZIP includes the dashboard in `templates/index.html` and its CSS/JavaScript in `static/`. Open only `http://127.0.0.1:5000/` after starting Flask; do not open `index.html` directly. The dashboard and API use the same local origin, so no CORS package is required.

# Phantom Stock-Out Detector

A beginner-friendly Python backend that flags products whose inventory system says stock exists while sales unexpectedly stop. It produces a ranked daily shelf-check list and a small Flask JSON API for a separately built frontend.

> **Important prototype disclaimer:** This Round-1 prototype uses synthetic data because organizer data has not yet been released. No real-world performance claim is made from the demo.

No paid APIs, databases, machine-learning libraries, cloud services, or external network calls are used. Pandas and CSV files are the main data and analytics layer.

## How it works

```text
Sales CSV ───────┐
Inventory CSV ───┼─> Schema mapping ─> Validation ─> Feature engineering
Optional CSVs ───┘                                      │
                                                        v
                                              Explainable risk score
                                                        │
                                                        v
                                      Ranked daily alerts (max 20/store/day)
                                                        │
                             ┌──────────────────────────┼──────────────────────┐
                             v                          v                      v
                      daily_alerts.csv           alert_history.csv       JSON metrics
                             │
                             v
                       Flask JSON API ─────────> Separate HTML/CSS/JS frontend
```

## Folder structure

```text
phantom-stock-detector-backend/
├── README.md
├── requirements.txt
├── .gitignore
├── app.py
├── run_pipeline.py
├── generate_demo_data.py
├── inspect_data.py
├── create_zip.py
├── config/
│   ├── schema.example.json
│   └── schema.demo.json
├── data/
├── output/
├── src/
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
```

## Prerequisites

- Python 3.10 or newer
- A terminal: PowerShell/Command Prompt on Windows, or Terminal on macOS/Linux
- Internet access only to install packages (the running application does not call external services)

## Install

### Windows PowerShell

```powershell
cd phantom-stock-detector-backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` and run commands with `.\.venv\Scripts\python.exe`.

### macOS / Linux

```bash
cd phantom-stock-detector-backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the demo

Run these commands from the project root:

```bash
python generate_demo_data.py
python inspect_data.py --schema config/schema.demo.json
python run_pipeline.py --schema config/schema.demo.json --evaluate --verbose
python app.py
```

Then open `http://127.0.0.1:5000/` in a browser or connect your separate frontend to the API. The pipeline creates output folders automatically. To run tests:

```bash
pytest
```

## API endpoints

All API responses are JSON except the CSV download route.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Project name and quick links |
| GET | `/api/health` | Output availability and row counts |
| GET | `/api/dates` | Sorted dates represented in daily alerts |
| GET | `/api/stores?date=YYYY-MM-DD` | Stores with alerts; date is optional |
| GET | `/api/alerts?date=YYYY-MM-DD&store_id=S001` | Ranked alerts for a store/date |
| GET | `/api/history?store_id=S001&sku_id=SKU003` | SKU/store daily series |
| GET | `/api/history?store_id=S001&sku_id=SKU003&start_date=2026-01-01&end_date=2026-03-01` | Filtered history |
| GET | `/api/summary` | Input counts, thresholds, date range, runtime |
| GET | `/api/recovery-estimate` | Illustrative scenario estimate |
| GET | `/download/daily-alerts` | Download ranked alert CSV |

If pipeline output is missing, the API returns a readable error instead of crashing. `/api/health` remains available to help diagnose this.

## Output files

- `output/daily_alerts.csv`: ranked inspection list, with a maximum of 20 candidates per store/date by default.
- `output/alert_history.csv`: time-series fields suitable for frontend charts, including candidate flag and score.
- `output/summary_metrics.json`: input counts, merged rows, candidates, alert count, stores, dates, thresholds, runtime, and disclaimer.
- `output/recovery_estimate.json`: scenario-based expected lost units and, where prices exist, potential revenue at risk.
- `output/evaluation_metrics.json`: created only when `--evaluate` is used.

The revenue figure is **not measured recovery**. Expected lost units are only a proxy calculated as historical expected daily demand multiplied by the zero-sales streak.

## Score and alert types

The heuristic score ranges from 0 to 100 and is deliberately transparent. Its configurable components reward positive on-hand stock, longer zero-sales streaks, prior demand, unchanged inventory, peer-store demand, and active promotions; slow-moving items receive a penalty. Weights and thresholds live in `src/config.py`.

An item becomes a candidate by default when:
- `on_hand > 0`
- zero-sales streak is at least 3 days
- historical expected demand is at least 0.50 units/day
- it is not flagged as a slow mover

Alert types:
- `likely_phantom_stockout`: the candidate has comparable stores still selling the SKU.
- `possible_wrong_shelf`: inventory has stayed unchanged for at least five days, without the peer-demand condition taking precedence.
- `monitor`: does not meet candidate conditions or needs more evidence.

These are risk flags, not proof. The tool never changes inventory automatically; a person must physically verify the shelf and backroom.

## Schema mapping

`config/schema.demo.json` maps the generated demo CSV column names. `config/schema.example.json` illustrates organizer columns with different names. In each section, `file` is the CSV path and each other mapping says which source column represents the standardized field. Required sections are `sales` and `inventory`; promotion, store, and product files are optional. Update the schema to match the organizer files instead of editing the analytics code first.

The internal required schemas are:

- Sales: `date`, `store_id`, `sku_id`, `units_sold`
- Inventory: `date`, `store_id`, `sku_id`, `on_hand`

Dates and numeric fields are parsed and invalid rows are excluded when safely possible. Duplicate date-store-SKU rows fail with a clear message because the pipeline cannot safely decide how to aggregate them.

## Replace demo data with organizer data

1. Keep a backup of the demo schema and generated CSVs.
2. Copy organizer CSVs into `data/` (or configure another relative path).
3. Open `config/schema.example.json` and change each `file` and source-column mapping to match the real headers.
4. Save your edited mapping as a new file, for example `config/schema.organizer.json`.
5. Inspect it: `python inspect_data.py --schema config/schema.organizer.json`
6. Run the pipeline: `python run_pipeline.py --schema config/schema.organizer.json --verbose`
7. Check the validation summary and manually inspect a sample of alerts before using them operationally.

If optional files are missing, the pipeline continues without those features. The exact organizer schema is not known yet, so mapping may need adjustment once the files are released.

## Evaluation

The demo generator writes synthetic `demo_ground_truth.csv` labels for evaluation only. Scoring code never reads these labels. `--evaluate` computes precision@K per store-date and mean precision across groups that appear in the ground truth. These are synthetic-demo-only metrics and must not be presented as real-world model performance.

## Two-minute team demo

1. Say the problem: system stock can be positive even when customers cannot find the product.
2. Run `python generate_demo_data.py` to create reproducible sample CSVs.
3. Run `python run_pipeline.py --schema config/schema.demo.json --evaluate --verbose`.
4. Open `output/daily_alerts.csv` and show the highest-ranked items, scores, and plain-English reasons.
5. Run `python app.py`, then open `/api/health`, `/api/dates`, and an `/api/alerts` URL.
6. Explain that a manager verifies the shelf; the prototype never edits inventory.
7. Repeat the disclaimer: all demo results are synthetic and are not real-world performance claims.

## GitHub publication notes

- Commit source code and schema examples, not virtual environments or confidential input files.
- Demo CSVs are ignored by `.gitignore`; teammates can regenerate them with `python generate_demo_data.py`.
- Review the schema for local paths or sensitive data before pushing.
- Include this README and the prototype disclaimer in any presentation.

## Create the ZIP

From the parent directory, the generated archive is normally already provided with this project. To rebuild it from the project root:

```bash
python create_zip.py
```

The script writes `phantom-stock-detector-backend.zip` to the parent directory.

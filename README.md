# Mamaearth Returns & Growth Intelligence Pipeline

Returns seem to be eating into margins on a subset of orders. This repo proves it end to end in three connected layers:

1. **SQL layer** stores the order data and answers the reporting questions.
2. **Python layer** cleans the data, finds the real patterns and quantifies them.
3. **GenAI layer** turns the verified numbers into a Situation-Complication-Resolution narrative for ops and finance heads.

No layer reports a number it did not compute itself or receive from the layer before it.

## Repo structure

```
.
├── README.md
├── requirements.txt
├── sql/
│   ├── schema.sql          # 3 tables: customers, products, orders
│   ├── seed_data.sql       # INSERTs generated from the CSVs (blank cells become real NULL)
│   └── reports.sql         # 9 reports (a-i), exact output pasted above each query
├── data/
│   ├── customers.csv       # 45 rows (raw, never edited)
│   ├── products.csv        # 16 rows
│   └── orders.csv          # 180 rows
├── analysis/
│   ├── clean_and_eda.py    # Part 2, Tasks 1-10 + writes narrator/findings.json
│   └── visualize.py        # Part 2, Task 11, writes the 2 PNGs
├── visualizations/
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_trend.png
└── narrator/
    ├── findings.json           # written by clean_and_eda.py, never hand-typed
    ├── generate_narrative.py   # Gemini narrative + offline fallback + number checker
    └── sample_output.txt       # saved narrative that the checker validates
```

## How data flows between the layers

```
data/*.csv ──► sql/ (SQLite)      Part 1: reports on the RAW data (e.g. raw revenue = 99,860.20)
     │
     └──────► analysis/clean_and_eda.py ──► narrator/findings.json ──► narrator/generate_narrative.py
                      │                      (verified numbers)            (Gemini, or offline template)
                      └──► analysis/visualize.py ──► visualizations/*.png
```

- Part 1 and Part 2 both read the same raw CSVs, so they can be run in either order.
- Part 2's reconciliation uses Part 1's raw total (Rs 99,860.20) and explains the Rs 2,501.90 gap.
- Part 3 reads **only** `narrator/findings.json`, which Part 2 writes at its last step.

## Setup

Python 3.9+ is needed.

```
pip install -r requirements.txt
```

Run every command below from the repo root.

## Step 1: SQL layer (Part 1)

The SQL was run and verified on SQLite. It uses standard syntax, so it should also work on MySQL.

**SQLite (command line):**

```
sqlite3 mamaearth.db ".read sql/schema.sql" ".read sql/seed_data.sql" ".read sql/reports.sql"
```

**No sqlite3 installed?** Python ships with it:

```
python -c "import sqlite3; c=sqlite3.connect('mamaearth.db'); [c.executescript(open('sql/%s.sql' % n).read()) for n in ('schema','seed_data','reports')]; print(c.execute('SELECT COUNT(*) FROM orders').fetchone())"
```

**MySQL Workbench:** create and select a database, then open and run `schema.sql`, `seed_data.sql`, `reports.sql` in that order.

`schema.sql` drops and recreates the tables, so the whole sequence is safe to re-run. After loading, the counts are 45 customers, 16 products, 180 orders. Because the seed file inserts real `NULL`s, `COUNT(rating)` is correctly 165 (no `.import` cleanup needed).

## Step 2: Python layer (Part 2)

```
python analysis/clean_and_eda.py
python analysis/visualize.py
```

`clean_and_eda.py` prints every task under its own banner. **Its last step writes `narrator/findings.json`**, so Part 3 always uses the numbers Part 2 just computed. `visualize.py` rebuilds the cleaned data from the raw CSVs and saves both charts to `visualizations/`.

## Step 3: GenAI narrator (Part 3)

```
python narrator/generate_narrative.py
```

**With no API key (offline path):** nothing to configure. The script builds the narrative from a fixed template using `findings.json`, with no network call.

**With a Gemini key:** get a free key from [Google AI Studio](https://aistudio.google.com/) (free tier, no paid key needed), set it as an environment variable, then run the same command.

```
# Windows PowerShell
$env:GEMINI_API_KEY = "your-key-here"

# Windows cmd
set GEMINI_API_KEY=your-key-here

# macOS / Linux
export GEMINI_API_KEY="your-key-here"
```

If the key is set but the API call fails (bad key, no network, quota), the script prints the reason and falls back to the offline template. It never crashes.

Each run finishes with a **numeric accuracy check** that confirms all five required figures appear in the narrative: 97,358.30 / 44.4 / 54.5 / 2,501.90 / March with 20,318.90. A live Gemini run saves its output to `narrator/sample_output.txt` (the first line states the source). The offline path never overwrites a saved Gemini sample.

## Numbers you should reproduce

| Layer | Figure | Value |
|---|---|---|
| SQL (a) | Orders / revenue / average order | 180 / 99,860.20 / 554.78 |
| SQL (b) | COUNT(*) / COUNT(rating) / gap | 180 / 165 / 15 |
| SQL (c) | Customer with zero orders | C045 Vihaan |
| SQL (d) | Cities with return rate over 20% | Jaipur 42.1, Lucknow 30.6, Bangalore 24.2 |
| SQL (i) | Gold / Silver | 28 / 17 |
| Python | After de-duplication | 175 rows (O0176-O0180 dropped) |
| Python | Cleaned revenue | 97,358.30 (gap of 2,501.90 = the 5 duplicates) |
| Python | Return rate CARD / COD / UPI | 14.7 / 44.4 / 18.9 |
| Python | Highest-risk segment | COD + Tier-2 at 54.5 |
| Python | True peak month | March 2026, Rs 20,318.90 (January only looked highest because of 2 bulk orders) |

## Notes on design choices

- **No hand-cleaned data.** The CSVs in `data/` are exactly as provided; all cleaning happens in Python.
- **Outliers are flagged, not deleted** (`is_outlier`), then excluded only where the time series needs it.
- **temperature = 0.0** in the Gemini call because this is a factual business report that should be repeatable.

# 📦 Mamaearth Returns & Growth Intelligence Pipeline

The Growth Analytics team suspects that **returns are eating into margins** on a subset of orders, but nobody had proved it end to end.

This project builds the full pipeline in three connected layers: a **SQL store with reports**, a **Python analysis layer** that cleans the data and finds the real patterns, and a **GenAI narrator** that turns the verified numbers into a short story ops and finance heads can act on.

One rule runs through the whole project: **no layer reports a number it did not calculate itself or receive from the layer before it.**

---

## 🔌 Data Source

All three layers start from the same three raw CSV files in `data/`:

- `customers.csv` (45 rows)
- `products.csv` (16 rows)
- `orders.csv` (180 rows)

The raw files are never edited by hand. Every fix happens in code, so the whole project can be re-run from scratch.

This ensures:

- Repeatable results ♻️
- No hidden manual changes ✅
- Numbers that match across all three layers 🎯

---

## 🗂️ Repository Structure

```
README.md
requirements.txt
sql/
    schema.sql
    seed_data.sql
    reports.sql
data/
    customers.csv
    products.csv
    orders.csv
analysis/
    clean_and_eda.py
    visualize.py
visualizations/
    return_rate_by_payment.png
    monthly_revenue_trend.png
narrator/
    findings.json
    generate_narrative.py
    sample_output.txt
```

---

## 🔗 How the Layers Connect

- The **SQL layer** and the **Python layer** both read the same raw CSV files, so they can be run in either order.
- The SQL layer gives the raw revenue total of **Rs 99,860.20**. The Python layer uses it to explain why the cleaned total is lower (**Rs 97,358.30**): the Rs 2,501.90 gap is exactly the 5 duplicate orders that were removed.
- The last step of `clean_and_eda.py` writes the verified results into `narrator/findings.json`.
- The **GenAI layer** reads only `findings.json`, so the story is always built from the numbers the analysis just produced.

---

## 📊 Project Layers

### 1. SQL Layer (`sql/`)

- `schema.sql` creates the 3 tables: `customers`, `products` and `orders`
- `seed_data.sql` loads the CSV data. Blank discount and rating cells are stored as real `NULL`, not zero
- `reports.sql` has 9 reports (a to i), with the exact output pasted above each query:
  - Order totals, revenue and average order value
  - `COUNT(*)` vs `COUNT(rating)` to expose missing ratings
  - `LEFT JOIN` check for customers with zero orders (cross-checked with `NOT IN`)
  - Return rate by city using `GROUP BY` and `HAVING`
  - Top spenders using `ORDER BY`, `LIMIT` and `OFFSET`
  - Category revenue from a three-table `JOIN`
  - `LIKE` and `DISTINCT` lookups
  - `ALTER TABLE` and `UPDATE` with `CASE` for loyalty tiers

### 2. Python Analysis Layer (`analysis/`)

`clean_and_eda.py` runs 10 tasks, each printed under its own heading:

- Load and inspect the three files
- Standardize payment method spelling (7 raw values become 3)
- Remove 5 duplicate orders
- Fill missing discounts and ratings
- Merge the tables and reconcile the total against the SQL layer
- Detect quantity outliers with the IQR method
- Test the hypothesis that COD has a higher return rate
- Segment return rates by payment method and city tier
- Check correlations
- Build an outlier-corrected monthly revenue series
- Write `narrator/findings.json`

`visualize.py` draws the two charts into `visualizations/`.

### 3. GenAI Narrator Layer (`narrator/`)

`generate_narrative.py` writes a Situation, Complication and Resolution narrative:

- Uses the Gemini API (free tier) with a system instruction and `temperature=0.0`
- Falls back to a fixed offline template if there is no key or the call fails
- Checks that all 5 required figures appear in the narrative and prints PASS or FAIL for each

---

## 🚀 How to Run

Open the repo folder in VS Code, open a terminal (Terminal, then New Terminal) and install the libraries once:

```
pip install -r requirements.txt
```

### Step 1: SQL Layer (MySQL Workbench)

1. Open MySQL Workbench and connect to your local instance.
2. Create and select a database:

```
CREATE DATABASE IF NOT EXISTS mamaearth;
USE mamaearth;
```

3. Go to File, then Open SQL Script, choose `sql/schema.sql` and click the lightning bolt to run it. It drops old copies first, so it is safe to re-run.
4. Do the same with `sql/seed_data.sql`, then check the counts:

```
SELECT COUNT(*) FROM customers;   -- 45
SELECT COUNT(*) FROM products;    -- 16
SELECT COUNT(*) FROM orders;      -- 180
```

5. Open `sql/reports.sql`. To run one report, select that query and click the lightning bolt. Compare your result with the output in the comment above it.

Two things to know about `reports.sql`:

- Report (i) updates every row with no `WHERE` clause, which Workbench blocks by default (Error 1175). Run `SET SQL_SAFE_UPDATES = 0;` once before that `UPDATE`.
- Report (i) adds a `loyalty_tier` column, which can only be added once. Running it twice gives Error 1060 (duplicate column), which is harmless. To start fresh, run `schema.sql` and `seed_data.sql` again.

### Step 2: Python Layer (VS Code)

Run these from the repo folder, in this order:

```
python analysis/clean_and_eda.py
python analysis/visualize.py
```

If `python` is not recognised, use `py` instead. The first script prints every task and **writes `narrator/findings.json` at the end**. The second saves both charts. Both find the data folder on their own, so they work from any terminal folder, and re-running gives identical numbers and files.

### Step 3: GenAI Narrator

```
python narrator/generate_narrative.py
```

**With no API key:** just run it. The offline template builds the narrative from `findings.json` with no internet and no setup.

**With a Gemini API key:** get a free key from Google AI Studio (aistudio.google.com), set it in the VS Code terminal, then run the script:

```
$env:GEMINI_API_KEY = "paste-your-key-here"
python narrator/generate_narrative.py
```

The key only lasts for that terminal window. If a key is set but the call fails (wrong key, no internet, quota used up), the script prints the reason and switches to the offline template by itself, so it never crashes.

A run with a Gemini key saves Gemini's text into `narrator/sample_output.txt` (the first line says which source wrote it). A run without a key only creates that file if it is missing, so it never overwrites a Gemini sample.

---

## 🎯 Key Findings

SQL layer:

- 180 orders, Rs 99,860.20 total revenue, Rs 554.78 average order value
- 165 of 180 orders have a rating (15 are un-rated)
- C045 (Vihaan) is the only customer with zero orders
- Cities with return rate above 20%: Jaipur 42.1%, Lucknow 30.6%, Bangalore 24.2%
- Loyalty tiers: Gold 28, Silver 17

Python layer:

- 5 duplicate orders removed (O0176 to O0180), leaving 175 rows
- Cleaned revenue is Rs 97,358.30, which is Rs 2,501.90 less than the raw total
- Return rate by payment method: **COD 44.4%**, UPI 18.9%, Card 14.7%
- Highest-risk segment: **COD orders in Tier 2 cities at 54.5%**
- Real peak month is **March 2026 at Rs 20,318.90**. January only looked highest (Rs 29,582.10) because of two bulk orders, and drops to Rs 11,637.10 without them
- Discounts do not reduce returns (correlation is negligible)

---

## ✨ Key Features

- Fully repeatable pipeline, from raw CSV to final narrative
- Reconciliation that explains the exact Rs 2,501.90 gap between layers
- Outliers are flagged and kept, then left out only where they would mislead
- Number checker that confirms the narrative contains the verified figures
- Works with a free Gemini key or with no key at all

---

## 🛠️ Tools Used

- **MySQL Workbench** and **SQL** for the relational layer
- **Python** with **pandas** and **Matplotlib** for analysis and charts
- **Google Gemini API** (`google-genai`) for the narrative
- **VS Code** for development
- **Git and GitHub** for version control and submission

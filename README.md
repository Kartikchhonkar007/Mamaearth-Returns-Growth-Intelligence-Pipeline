# Mamaearth Returns & Growth Intelligence Pipeline

This project looks at a simple business question: are product returns affecting revenue, and can we identify the orders or customer segments where the problem is bigger?

I built the pipeline using MySQL, Python, and a small GenAI layer. It starts with raw CSV files, uses SQL and Python to analyze the data, and then turns the findings into a short business summary. The aim is to keep the numbers traceable from the original data through to the final narrative.

## Tools Used

- **MySQL** for tables, data loading, and reporting
- **Python** with Pandas for cleaning and analysis
- **Matplotlib** for charts
- **Google Gemini API** for generating a written summary
- **Git and GitHub** for version control

## Project Structure

```text
├── data/
│   ├── customers.csv
│   ├── products.csv
│   └── orders.csv
├── sql/
│   ├── schema.sql
│   ├── seed_data.sql
│   └── reports.sql
├── analysis/
│   ├── clean_and_eda.py
│   └── visualize.py
├── visualizations/
│   ├── return_rate_by_payment.png
│   └── monthly_revenue_trend.png
├── narrator/
│   ├── findings.json
│   ├── generate_narrative.py
│   └── sample_output.txt
├── requirements.txt
└── README.md
```

## How It Works

The project has three parts:

1. **SQL:** Creates the customer, product, and order tables, loads the data, and runs nine reports.
2. **Python:** Cleans the data, standardizes payment method names, removes duplicate orders, checks outliers, and looks at return rates across payment methods and city tiers.
3. **GenAI narrator:** Reads the results saved in `narrator/findings.json` and writes a short Situation, Complication, and Resolution summary. It uses Gemini when an API key is available and has an offline fallback.

Both SQL and Python start from the same raw CSV files. The raw files are not edited manually, so the steps can be repeated.

## Key Findings

The dataset contains 180 orders before cleaning. The Python analysis removes five duplicate orders, leaving 175 orders.

| Metric | Result |
|---|---:|
| Orders in raw data | 180 |
| Duplicate orders removed | 5 |
| Orders after cleaning | 175 |
| Revenue before cleaning (SQL) | ₹99,860.20 |
| Revenue after cleaning (Python) | ₹97,358.30 |
| Difference | ₹2,501.90 |
| COD return rate | 44.4% |
| UPI return rate | 18.9% |
| Card return rate | 14.7% |
| Return rate for Tier 2 COD orders | 54.5% |

COD has the highest return rate among the three payment methods in this dataset. The highest-risk segment is COD orders from Tier 2 cities, with a return rate of 54.5%. This is a useful area for further investigation, rather than proof of the cause of returns.

The revenue difference of ₹2,501.90 matches the value associated with the five duplicate orders removed during cleaning.

The monthly revenue analysis also shows why it is worth checking unusually large orders before drawing conclusions from a chart. March 2026 is the peak month after accounting for the bulk-order outliers.

## Charts

### Return Rate by Payment Method

![Return Rate by Payment Method](visualizations/return_rate_by_payment.png)

### Monthly Revenue Trend

![Monthly Revenue Trend](visualizations/monthly_revenue_trend.png)

## How to Run the Project

### 1. Install the Python libraries

Run this from the repository folder:

```bash
pip install -r requirements.txt
```

### 2. Set up the SQL database

Open MySQL Workbench and run:

```sql
CREATE DATABASE IF NOT EXISTS mamaearth;
USE mamaearth;
```

Then run these scripts in order:

1. `sql/schema.sql`
2. `sql/seed_data.sql`
3. `sql/reports.sql`

Check that the data loaded correctly:

```sql
SELECT COUNT(*) FROM customers; -- Expected: 45
SELECT COUNT(*) FROM products;  -- Expected: 16
SELECT COUNT(*) FROM orders;    -- Expected: 180
```

Report (i) updates loyalty tiers and adds a `loyalty_tier` column. If MySQL Workbench blocks the update because safe-update mode is on, disable safe updates for the session. If you want to run the report from scratch again, rerun the schema and seed scripts first because the column can only be added once.

### 3. Run the Python scripts

From the repository root, run:

```bash
python analysis/clean_and_eda.py
python analysis/visualize.py
```

The first script prints the analysis steps and saves the findings to `narrator/findings.json`. The second creates the charts in the `visualizations/` folder.

If `python` is not recognized on Windows, try `py` instead.

### 4. Generate the narrative

Run:

```bash
python narrator/generate_narrative.py
```

Without an API key, the script uses the offline template. To use Gemini in PowerShell, set your key in the current terminal:

```powershell
$env:GEMINI_API_KEY = "your-api-key"
python narrator/generate_narrative.py
```

Keep the API key private and do not commit it to GitHub. If the Gemini request fails, the script falls back to the offline template.

## Data Checks

A few checks are built into the workflow:

- The raw CSV files stay unchanged.
- Duplicate orders are removed in code, not by editing the files manually.
- Missing discounts and ratings are handled by the Python cleaning step; blank discount and rating cells are loaded as SQL `NULL` in the SQL layer.
- The Python analysis compares cleaned revenue with the SQL revenue and explains the difference.
- Outliers are flagged. Bulk orders are excluded only from the adjusted monthly revenue comparison where they would distort the trend.
- The narrator checks whether five required figures appear in its output and prints a PASS or FAIL for each check. This checks for the figures' presence, not whether every sentence generated by the model is factually correct.

## What I Learned

This project gave me practice connecting SQL reporting with Python analysis instead of treating them as separate tasks. It also helped me think more carefully about duplicate records, missing values, outliers, and making sure a business summary can be traced back to calculated results.

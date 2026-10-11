import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")   # draw straight to files, no window needed
import matplotlib.pyplot as plt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT_DIR = os.path.join(ROOT, 'visualizations')
os.makedirs(OUT_DIR, exist_ok=True)

# ---- rebuild the cleaned, merged data from the raw CSVs (same steps as clean_and_eda.py) ----
orders = pd.read_csv(os.path.join(ROOT, 'data', 'orders.csv'))
customers = pd.read_csv(os.path.join(ROOT, 'data', 'customers.csv'))
products = pd.read_csv(os.path.join(ROOT, 'data', 'products.csv'))

orders['payment_method'] = orders['payment_method'].str.strip().str.upper()

key_cols = ['customer_id', 'product_id', 'order_date', 'quantity',
            'discount_pct', 'payment_method', 'rating', 'returned']
orders = orders[~orders.duplicated(subset=key_cols, keep='first')].reset_index(drop=True)

orders['discount_pct'] = orders['discount_pct'].fillna(0)
orders['rating'] = orders['rating'].fillna(orders['rating'].median())

merged = orders.merge(products, on='product_id').merge(customers, on='customer_id')
merged['order_value'] = merged['quantity'] * merged['price'] * (1 - merged['discount_pct'] / 100)

q1, q3 = merged['quantity'].quantile(0.25), merged['quantity'].quantile(0.75)
iqr = q3 - q1
merged['is_outlier'] = (merged['quantity'] < q1 - 1.5 * iqr) | (merged['quantity'] > q3 + 1.5 * iqr)


# ---- Chart 1: return rate by payment method ----
rates = (merged.groupby('payment_method')['returned'].mean() * 100).round(1)
rates = rates.sort_values(ascending=False)

top_method, top_rate = rates.index[0], rates.iloc[0]
low_method, low_rate = rates.index[-1], rates.iloc[-1]
ratio = round(top_rate / low_rate)

fig, ax = plt.subplots(figsize=(8, 5))
colors = ['#c0392b'] + ['#7f8c8d'] * (len(rates) - 1)
bars = ax.bar(rates.index, rates.values, color=colors)
for bar, val in zip(bars, rates.values):
    ax.text(bar.get_x() + bar.get_width() / 2, val + 0.8, f"{val}%",
            ha='center', va='bottom', fontsize=12, fontweight='bold')
ax.set_title(f"{top_method} Returns at {top_rate}% \u2014 {ratio}x {low_method.title()}", fontsize=14)
ax.set_xlabel("Payment method")
ax.set_ylabel("Return rate (%)")
ax.set_ylim(0, rates.max() * 1.2)
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, 'return_rate_by_payment.png'), dpi=150)
plt.close(fig)
print("Saved visualizations/return_rate_by_payment.png")


# ---- Chart 2: outlier-corrected monthly revenue ----
merged['year_month'] = pd.to_datetime(merged['order_date']).dt.strftime('%Y-%m')
monthly = merged[~merged['is_outlier']].groupby('year_month')['order_value'].sum().round(2)

peak_month = monthly.idxmax()
peak_value = monthly.max()
peak_label = pd.Period(peak_month, freq='M').strftime('%B %Y')
month_labels = [pd.Period(m, freq='M').strftime('%b %Y') for m in monthly.index]

fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(month_labels, monthly.values, marker='o', linewidth=2, color='#2c3e50')
peak_idx = list(monthly.index).index(peak_month)
ax.scatter([month_labels[peak_idx]], [peak_value], s=140, color='#c0392b', zorder=3)
ax.annotate(f"Peak: Rs {peak_value:,.2f}", (month_labels[peak_idx], peak_value),
            textcoords="offset points", xytext=(0, 12), ha='center', fontweight='bold')
ax.set_title(f"Outlier-Corrected Monthly Revenue \u2014 Peak in {peak_label}", fontsize=14)
ax.set_xlabel("Month")
ax.set_ylabel("Revenue (Rs)")
ax.set_ylim(0, monthly.max() * 1.2)
ax.grid(axis='y', alpha=0.3)
ax.spines[['top', 'right']].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(OUT_DIR, 'monthly_revenue_trend.png'), dpi=150)
plt.close(fig)
print("Saved visualizations/monthly_revenue_trend.png")

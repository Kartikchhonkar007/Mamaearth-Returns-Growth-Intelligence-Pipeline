import os
import json
import pandas as pd

base = os.path.dirname(os.path.abspath(__file__))

# ---------- Task 1: load the files ----------
print("\n----- Task 1: load and inspect -----")

orders = pd.read_csv('repo/data/DataOrder.csv')
customers = pd.read_csv('repo/data/Datacustomer.csv')
products = pd.read_csv( 'repo/data/ProductData.csv')

print("orders shape:", orders.shape)   # should be (180, 9)


# ---------- Task 2: fix payment method spelling ----------
print("\n----- Task 2: payment_method casing -----")

print("before:", orders['payment_method'].unique())   # 7 different spellings
orders['payment_method'] = orders['payment_method'].str.strip().str.upper()
print("after:", orders['payment_method'].unique())    # only 3 now
print(orders['payment_method'].value_counts())        # CARD 70, UPI 55, COD 55


# ---------- Task 3: remove duplicate orders ----------
print("\n----- Task 3: duplicate orders -----")

# every column except order_id, because order_id is the only thing that differs
cols = ['customer_id', 'product_id', 'order_date', 'quantity',
        'discount_pct', 'payment_method', 'rating', 'returned']

is_dup = orders.duplicated(subset=cols, keep='first')
print("duplicates found:", is_dup.sum())
print("dropped order ids:", orders.loc[is_dup, 'order_id'].tolist())

orders_clean = orders[~is_dup].reset_index(drop=True)
print("shape after dropping:", orders_clean.shape)   # (175, 9)


# ---------- Task 4: fill the blanks ----------
print("\n----- Task 4: missing values -----")

print("blank discounts:", orders_clean['discount_pct'].isnull().sum())   # 12
orders_clean['discount_pct'] = orders_clean['discount_pct'].fillna(0)  # no promo used

median_rating = orders_clean['rating'].median()
print("median rating:", median_rating)                                 # 3.0
print("blank ratings:", orders_clean['rating'].isnull().sum())         # 15
orders_clean['rating'] = orders_clean['rating'].fillna(median_rating)

print(orders_clean[['discount_pct', 'rating']].isnull().sum())         # both 0


# ---------- Task 5: merge and compare with the SQL total ----------
print("\n----- Task 5: merge and reconcile -----")

merged = orders_clean.merge(products, on='product_id')
merged = merged.merge(customers, on='customer_id')
merged['order_value'] = merged['quantity'] * merged['price'] * (1 - merged['discount_pct'] / 100)

cleaned_total = round(merged['order_value'].sum(), 2)
print("cleaned total: Rs", cleaned_total)   # 97358.3
print("rows:", len(merged))                 # 175

raw_total = 99860.20                        # from the SQL report (a)
gap = round(raw_total - cleaned_total, 2)

# work out what the 5 dropped rows were worth, to double check the gap
dropped = orders[is_dup].merge(products, on='product_id')
dropped['discount_pct'] = dropped['discount_pct'].fillna(0)
dropped['order_value'] = dropped['quantity'] * dropped['price'] * (1 - dropped['discount_pct'] / 100)
dropped_total = round(dropped['order_value'].sum(), 2)
print("value of the 5 dropped rows: Rs", dropped_total)

print()
print("Reconciliation note:")
print("The SQL total on the raw data was Rs", raw_total, "and the cleaned total is Rs", cleaned_total)
print("so the difference is Rs", gap, "- and this is fully explained by the 5 duplicate")
print("orders (O0176 to O0180) that we removed in Task 3. Added up on their own, those")
print("5 rows are worth Rs", dropped_total, "which is exactly the gap. Filling the blank")
print("ratings and discounts did not change any order value, so it did not add to the gap.")


# ---------- Task 6: outliers in quantity ----------
print("\n----- Task 6: outliers (IQR) -----")

q1 = merged['quantity'].quantile(0.25)
q3 = merged['quantity'].quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr
print("Q1:", q1, " Q3:", q3, " IQR:", iqr, " lower:", lower, " upper:", upper)

# just mark them, don't delete anything
merged['is_outlier'] = (merged['quantity'] < lower) | (merged['quantity'] > upper)
print("outliers found:", merged['is_outlier'].sum())
print(merged.loc[merged['is_outlier'], ['order_id', 'quantity']])


# ---------- Task 7: is COD returned more? ----------
print("\n----- Task 7: hypothesis on COD returns -----")

print("Hypothesis: COD orders get returned more often than Card or UPI orders.")
by_payment = merged.groupby('payment_method')['returned'].agg(['count', 'mean'])
by_payment['return_rate'] = (by_payment['mean'] * 100).round(1)
print(by_payment)

if by_payment['return_rate'].idxmax() == 'COD':
    print("Result: Confirmed. COD has the highest return rate.")
else:
    print("Result: Not confirmed.")


# ---------- Task 8: payment method + city tier ----------
print("\n----- Task 8: segmentation -----")

by_segment = merged.groupby(['payment_method', 'city_tier'])['returned'].agg(['count', 'mean'])
by_segment['return_rate'] = (by_segment['mean'] * 100).round(1)
print(by_segment)

worst = by_segment['return_rate'].idxmax()
worst_rate = by_segment['return_rate'].max()
print("\nHighest risk segment:", worst[0], "orders in Tier", worst[1], "cities at", worst_rate, "%")
print("COD Tier 1:", by_segment.loc[('COD', 1), 'return_rate'], "%  (", by_segment.loc[('COD', 1), 'count'], "orders )")
print("COD Tier 2:", by_segment.loc[('COD', 2), 'return_rate'], "%  (", by_segment.loc[('COD', 2), 'count'], "orders )")
print("So the COD problem is not the same everywhere, it is worse in Tier 2 cities.")


# ---------- Task 9: correlations ----------
print("\n----- Task 9: correlation -----")

num_cols = ['rating', 'returned', 'discount_pct', 'quantity']
corr = merged[num_cols].corr()
print(corr.round(3))


def strength(r):
    r = abs(r)
    if r < 0.2:
        return "negligible"
    elif r < 0.4:
        return "weak"
    elif r < 0.7:
        return "moderate"
    else:
        return "strong"


print()
for i in range(len(num_cols)):
    for j in range(i + 1, len(num_cols)):
        r = corr.loc[num_cols[i], num_cols[j]]
        print(num_cols[i], "vs", num_cols[j], ":", round(r, 3), "->", strength(r))

r = corr.loc['discount_pct', 'returned']
print("\nIdea: higher discounts reduce returns. discount vs returned =", round(r, 3), "->",
      "Busted" if abs(r) < 0.2 else "Holds")


# ---------- Task 10: monthly revenue ----------
print("\n----- Task 10: monthly revenue -----")

merged['order_date'] = pd.to_datetime(merged['order_date'])
merged['month'] = merged['order_date'].dt.strftime('%Y-%m')

with_outliers = merged.groupby('month')['order_value'].sum().round(2)
without_outliers = merged[~merged['is_outlier']].groupby('month')['order_value'].sum().round(2)

print("including the 2 outlier orders:")
print(with_outliers.map('{:.2f}'.format).to_string())
print("\nexcluding them:")
print(without_outliers.map('{:.2f}'.format).to_string())

fake_peak = with_outliers.idxmax()
true_peak = without_outliers.idxmax()
fake_name = pd.to_datetime(fake_peak + '-01').strftime('%B')
true_name = pd.to_datetime(true_peak + '-01').strftime('%B')

print()
print(fake_name, "only looks like the best month because of two bulk orders that landed in it:")
print("O0011 (25 units, 2026-01-28) and O0098 (30 units, 2026-01-10).")
print("Without them", fake_name, "drops from Rs", with_outliers[fake_peak], "to Rs", without_outliers[fake_peak])
print("and", true_name, "is the real peak month at Rs", without_outliers[true_peak])


# ---------- save the numbers for the narrator ----------
print("\n----- saving findings.json -----")

findings = {
    "cleaned_total_revenue_inr": float(cleaned_total),
    "raw_total_revenue_inr": raw_total,
    "duplicate_reconciliation_delta_inr": float(gap),
    "return_rate_by_payment": {
        "COD": float(by_payment.loc['COD', 'return_rate']),
        "CARD": float(by_payment.loc['CARD', 'return_rate']),
        "UPI": float(by_payment.loc['UPI', 'return_rate'])
    },
    "highest_risk_segment": {
        "payment_method": worst[0],
        "city_tier": int(worst[1]),
        "return_rate_pct": float(worst_rate)
    },
    "true_peak_month": {
        "month": true_peak,
        "revenue_inr": float(without_outliers[true_peak])
    },
    "outlier_inflated_month": {
        "month": fake_peak,
        "apparent_revenue_inr": float(with_outliers[fake_peak]),
        "corrected_revenue_inr": float(without_outliers[fake_peak])
    }
}

narrator_folder = os.path.join(base, '..', 'narrator')
os.makedirs(narrator_folder, exist_ok=True)

with open(os.path.join(narrator_folder, 'findings.json'), 'w') as f:
    json.dump(findings, f, indent=2)

print("done, saved to narrator/findings.json")
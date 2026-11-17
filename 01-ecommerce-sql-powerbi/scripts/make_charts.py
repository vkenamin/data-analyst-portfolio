"""
Build the README charts from results/*.csv (run export_results.py first).
    python scripts/make_charts.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES, OUT = ROOT / "results", ROOT / "charts"
OUT.mkdir(exist_ok=True)

BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#b8b6ae"
INK, INK2, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": "#d6d5cf", "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#ecebe7", "grid.linewidth": 0.8,
    "font.size": 11, "axes.titlesize": 14, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.axisbelow": True,
})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=160)
    plt.close(fig)


# 1. Monthly revenue trend
m = pd.read_csv(RES / "q02_monthly_revenue.csv", parse_dates=["month"])
fig, ax = plt.subplots(figsize=(10, 4.8))
ax.plot(m["month"], m["revenue_brl"] / 1e3, color=BLUE, lw=2, marker="o", ms=5)
peak = m.loc[m["revenue_brl"].idxmax()]
ax.annotate(f"Black Friday month\nR${peak.revenue_brl/1e3:,.0f}K (+{peak.mom_growth_pct:.0f}% MoM)",
            (peak.month, peak.revenue_brl / 1e3), xytext=(-175, -45), textcoords="offset points",
            color=INK2, fontsize=10, arrowprops=dict(arrowstyle="-", color=INK2))
ax.set_title("Monthly revenue, delivered orders (Jan 2017 – Aug 2018)")
ax.set_ylabel("Revenue (R$ thousands)")
ax.set_ylim(0, m["revenue_brl"].max() / 1e3 * 1.12)
save(fig, "01_monthly_revenue.png")

# 2. Late delivery vs review score
d = pd.read_csv(RES / "q05_delivery_vs_reviews.csv")
fig, ax = plt.subplots(figsize=(8, 4.6))
colors = [BLUE, ORANGE, ORANGE]
bars = ax.bar(d["delivery_status"], d["pct_1_or_2_star"], color=colors, width=0.55)
for b, pct, n, score in zip(bars, d["pct_1_or_2_star"], d["pct_of_orders"], d["avg_review_score"]):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5,
            f"{pct:.0f}% low reviews\navg {score:.2f}★ · {n:.1f}% of orders",
            ha="center", fontsize=10, color=INK)
ax.set_title("Late deliveries drive 1–2 star reviews")
ax.set_ylabel("Share of orders with a 1–2 star review")
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_ylim(0, 100)
ax.grid(axis="x", visible=False)
save(fig, "02_delivery_vs_reviews.png")

# 3. Top categories
c = pd.read_csv(RES / "q04_top_categories.csv").head(10).iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(c["category"].str.replace("_", " "), c["revenue_brl"] / 1e6, color=BLUE, height=0.6)
for y, (v, s) in enumerate(zip(c["revenue_brl"] / 1e6, c["share_pct"])):
    ax.text(v + 0.02, y, f"R${v:.2f}M · {s:.1f}%", va="center", fontsize=10, color=INK2)
ax.set_title("Top 10 categories by revenue")
ax.set_xlabel("Revenue (R$ millions)")
ax.set_xlim(0, c["revenue_brl"].max() / 1e6 * 1.3)
ax.grid(axis="y", visible=False)
save(fig, "03_top_categories.png")

# 4. Revenue concentration by customer decile
p = pd.read_csv(RES / "q10_pareto_customers.csv")
fig, ax = plt.subplots(figsize=(9, 4.6))
cols = [ORANGE, ORANGE] + [GRAY] * 8
ax.bar(p["decile"].astype(str), p["pct_revenue"], color=cols, width=0.6)
for x, v in enumerate(p["pct_revenue"]):
    ax.text(x, v + 0.8, f"{v:.1f}%", ha="center", fontsize=10, color=INK2)
top20 = p.loc[p["decile"] == 2, "cumulative_pct_revenue"].item()
ax.set_title(f"Top 20% of customers bring {top20:.0f}% of revenue")
ax.set_xlabel("Customer decile by spend (1 = top 10%)")
ax.set_ylabel("Share of revenue")
ax.yaxis.set_major_formatter(mtick.PercentFormatter())
ax.grid(axis="x", visible=False)
save(fig, "04_customer_concentration.png")

# 5. Late delivery rate by state
s = pd.read_csv(RES / "q06_delivery_by_state.csv").sort_values("pct_late")
fig, ax = plt.subplots(figsize=(8, 5.5))
cols = [ORANGE if v >= 12 else BLUE for v in s["pct_late"]]
ax.barh(s["state"], s["pct_late"], color=cols, height=0.6)
for y, (v, days) in enumerate(zip(s["pct_late"], s["avg_days_to_deliver"])):
    ax.text(v + 0.3, y, f"{v:.1f}% · {days:.0f} days avg", va="center", fontsize=9, color=INK2)
ax.set_title("Late-delivery rate by customer state (500+ orders)")
ax.set_xlabel("Orders delivered after the promised date")
ax.xaxis.set_major_formatter(mtick.PercentFormatter())
ax.set_xlim(0, s["pct_late"].max() * 1.45)
ax.grid(axis="y", visible=False)
save(fig, "05_late_by_state.png")

print("charts saved to", OUT)

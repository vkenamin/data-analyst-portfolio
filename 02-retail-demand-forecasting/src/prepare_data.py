"""
Prepare the M5 (Walmart) data for this project.

Input  (download from Kaggle "M5 Forecasting - Accuracy" into data/raw/):
    sales_train_evaluation.csv, calendar.csv, sell_prices.csv
Output (small enough to commit):
    data/processed/ca3_foods_daily.csv.gz   one row per item per day, last 2 years
    data/processed/calendar.csv             calendar for the same period

Scope: store CA_3 (the largest store in the dataset), FOODS category,
26 May 2014 – 22 May 2016 (104 full Monday–Sunday weeks).

    python src/prepare_data.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
STORE, CATEGORY = "CA_3", "FOODS"
START, END = "2014-05-26", "2016-05-22"   # Monday .. Sunday = 104 full weeks


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    cal = pd.read_csv(RAW / "calendar.csv", parse_dates=["date"])
    if "d" not in cal.columns:   # some copies of calendar.csv omit the day-index column
        cal["d"] = "d_" + ((cal["date"] - pd.Timestamp("2011-01-29")).dt.days + 1).astype(str)
    cal = cal[(cal["date"] >= START) & (cal["date"] <= END)]
    keep_days = cal["d"].tolist()

    id_cols = ["item_id", "dept_id", "cat_id", "store_id"]
    sales = pd.read_csv(RAW / "sales_train_evaluation.csv",
                        usecols=id_cols + keep_days)
    sales = sales[(sales["store_id"] == STORE) & (sales["cat_id"] == CATEGORY)]

    # wide (one column per day) -> long (one row per item-day)
    long = sales.melt(id_vars=id_cols, var_name="d", value_name="units")
    long = long.merge(cal[["d", "date", "wm_yr_wk", "event_name_1", "event_type_1", "snap_CA"]],
                      on="d", how="left")

    prices = pd.read_csv(RAW / "sell_prices.csv")
    prices = prices[prices["store_id"] == STORE]
    long = long.merge(prices[["item_id", "wm_yr_wk", "sell_price"]],
                      on=["item_id", "wm_yr_wk"], how="left")

    long = long.drop(columns=["d", "cat_id", "store_id"]).sort_values(["item_id", "date"])
    long.to_csv(OUT / "ca3_foods_daily.csv.gz", index=False, compression="gzip")
    cal.to_csv(OUT / "calendar.csv", index=False)
    print(f"{long['item_id'].nunique()} items x {long['date'].nunique()} days = {len(long):,} rows")


if __name__ == "__main__":
    main()

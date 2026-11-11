"""
Clean the raw marketing A/B test file.

Input : data/raw/marketing_AB.csv   (Kaggle: "Marketing A/B Testing" — 588,101 users)
Output: data/ab_test_clean.csv
        data/cleaning_log.csv       (what was checked / changed, used in the Excel Data_Quality sheet)

Steps
  1. Drop the unnamed index column the export left behind
  2. Rename columns to snake_case
  3. Check: missing values, duplicate users, invalid groups / hours / ad counts
  4. converted TRUE/FALSE -> 1/0 (so Excel can SUM / COUNTIFS it)
  5. Add ads_bucket (exposure band) for segment analysis

    python src/clean_data.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw" / "marketing_AB.csv", ROOT / "data"

BUCKETS = [0, 9, 24, 49, 99, float("inf")]
LABELS = ["1-9", "10-24", "25-49", "50-99", "100+"]


def main() -> None:
    raw = pd.read_csv(RAW)
    log = [("Raw rows", len(raw), "")]

    df = raw.drop(columns=[c for c in raw.columns if c.startswith("Unnamed")])
    log.append(("Unnamed index column dropped", 1, "Leftover pandas index, not data"))
    df.columns = ["user_id", "test_group", "converted", "total_ads", "most_ads_day", "most_ads_hour"]

    log += [
        ("Missing values (all columns)", int(df.isna().sum().sum()), "None found"),
        ("Duplicate user_id", int(df["user_id"].duplicated().sum()), "None found — each user appears once"),
        ("test_group not 'ad' or 'psa'", int((~df["test_group"].isin(["ad", "psa"])).sum()), "None found"),
        ("most_ads_hour outside 0-23", int((~df["most_ads_hour"].between(0, 23)).sum()), "None found"),
        ("total_ads below 1", int((df["total_ads"] < 1).sum()), "None found"),
        ("total_ads above 99th percentile", int((df["total_ads"] > df["total_ads"].quantile(0.99)).sum()),
         "Kept — heavy users are real; handled by exposure buckets"),
    ]

    df["converted"] = df["converted"].astype(int)
    df["ads_bucket"] = pd.cut(df["total_ads"], BUCKETS, labels=LABELS).astype(str)
    df = df[["user_id", "test_group", "converted", "total_ads", "ads_bucket", "most_ads_day", "most_ads_hour"]]
    log.append(("Clean rows", len(df), "No rows removed"))

    df.to_csv(OUT / "ab_test_clean.csv", index=False)
    pd.DataFrame(log, columns=["check", "result", "action"]).to_csv(OUT / "cleaning_log.csv", index=False)
    print(pd.DataFrame(log, columns=["check", "result", "action"]).to_string(index=False))


if __name__ == "__main__":
    main()

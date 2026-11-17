# Tableau dashboard — data and design

## Data source

`ab_test_tableau_extract.csv` — the 588,101 user rows aggregated to **1,616 rows**
(test group × peak ad day × peak ad hour × exposure bucket), with `users`, `conversions` and `total_ads`.
Totals reconcile exactly with the raw data (588,101 users, 14,843 conversions).

## Calculated fields

Rates are always built from summed counts, never by averaging pre-computed rates:

```
Conversion Rate = SUM([Conversions]) / SUM([Users])

Ad Rate   = SUM(IF [Test Group] = "Ad"  THEN [Conversions] END) / SUM(IF [Test Group] = "Ad"  THEN [Users] END)
PSA Rate  = SUM(IF [Test Group] = "PSA" THEN [Conversions] END) / SUM(IF [Test Group] = "PSA" THEN [Users] END)

Lift (pp)       = ([Ad Rate] - [PSA Rate]) * 100
Relative Lift   = ([Ad Rate] - [PSA Rate]) / [PSA Rate]
PSA Conversions = SUM(IF [Test Group] = "PSA" THEN [Conversions] END)
Reliable?       = IF [PSA Conversions] >= 30 THEN "Yes" ELSE "Low sample" END
```

## Dashboard layout

**Title:** *Ads lift conversion 43% — but only after 25+ exposures*

1. **KPI row** — Ad rate 2.55%, PSA rate 1.79%, relative lift +43%, users 588,101.
2. **Conversion by group** — bar chart, Ad vs PSA.
3. **Lift by exposure** — lift (pp) per ads-seen bucket, coloured by the small-sample flag, reference line at 0.
4. **Day × hour heatmap** — ad conversion rate by the day and hour users saw the most ads.
5. **Ad vs PSA by day** — side-by-side bars.

Filters for peak ad day and exposure bucket apply to all sheets.
Caption: *Exposure wasn't randomised — read segment lifts as correlation, not causation.*

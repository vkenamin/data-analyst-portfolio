# Memo: should we roll out the ad campaign?

**To:** Marketing Manager **From:** Viken Amin, Data Analyst **Re:** Ad vs PSA conversion test (588,101 users)

## Recommendation
**Roll out the ad campaign, keep a small control group so we can keep measuring, and test how many
impressions it takes to work — the lift only appeared after 25+ exposures.**

## What we found
- **The ad works.** Users who saw the ad converted at **2.55%** vs **1.79%** for the public-service-ad control —
  a **43% relative lift**. A gap this large would almost never appear by chance if the ad had no effect
  (p < 0.001), and the 95% confidence interval puts the true lift between **+0.60 and +0.94 percentage points**.
- **About 4,300 extra conversions** came from the ad over the test period — conversions that would not have
  happened otherwise. Multiplying by average order value gives the campaign's incremental revenue (the
  workbook has an input cell for this).
- **Frequency matters.** Users who saw fewer than 25 ads converted no better than the control group. The lift appears
  at 25–49 ads (+0.8 pp) and is largest at 50+ ads (+5–6 pp). Heavier users naturally see more ads, so this is a
  strong signal rather than proof — a follow-up test should randomise frequency directly.
- **Day pattern:** the lift was largest when users saw most of their ads on **Monday and Tuesday**, and not
  significant for Thursday and Sunday.

## Caveats
- The control group was only 4% of users. Enough to prove this effect, but too small to detect lifts under ~14%.
  A future test of smaller changes (new creative, new copy) needs a larger control group.
- The data has no revenue or cost, so return on ad spend can't be calculated yet.

## Next steps
1. Roll out; hold back 5–10% as a permanent control.
2. Test frequency caps (e.g. 25 vs 50 vs uncapped impressions) with random assignment.
3. Join conversion data to order values to calculate return on ad spend.

"""
Build excel/ab_test_analysis.xlsx from data/ab_test_clean.csv.

Every number in the analysis sheets is a live Excel formula over the Data sheet
(COUNTIFS, NORMSDIST, CHITEST, ...). Python also computes each result and stores
it as the formula's cached value, so previews show correct numbers before Excel
recalculates. src/verify_workbook.py checks both agree.

    python src/build_workbook.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import xlsxwriter

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data" / "ab_test_clean.csv")
log = pd.read_csv(ROOT / "data" / "cleaning_log.csv")
OUT = ROOT / "excel" / "ab_test_analysis.xlsx"
OUT.parent.mkdir(exist_ok=True)

N = len(df)
LAST = N + 1                       # last data row in Excel (row 1 = header)
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
BUCKETS = ["1-9", "10-24", "25-49", "50-99", "100+"]
ALPHA = 0.05

wb = xlsxwriter.Workbook(OUT, {"constant_memory": False, "strings_to_numbers": False})
wb.set_properties({"title": "Marketing A/B Test Analysis", "author": "Viken Amin"})

# ---------------------------------------------------------------- formats
FONT = "Arial"
def F(**kw):
    base = {"font_name": FONT, "font_size": 10, "valign": "vcenter"}
    base.update(kw)
    return wb.add_format(base)

f_title = F(bold=True, font_size=16, font_color="#0b0b0b")
f_sub = F(italic=True, font_color="#52514e")
f_h2 = F(bold=True, font_size=12, font_color="#0b0b0b", bottom=1, bottom_color="#d6d5cf")
f_hdr = F(bold=True, bg_color="#1f3a5f", font_color="white", border=1, border_color="#d6d5cf", text_wrap=True, align="center")
f_lbl = F(border=1, border_color="#e3e2dc")
f_lbl_b = F(border=1, border_color="#e3e2dc", bold=True)
f_txt = F(text_wrap=True, valign="top")
f_note = F(italic=True, font_color="#52514e", text_wrap=True, valign="top", font_size=9)
f_int = F(num_format="#,##0", border=1, border_color="#e3e2dc")
f_pct = F(num_format="0.00%", border=1, border_color="#e3e2dc")
f_pct1 = F(num_format="0.0%", border=1, border_color="#e3e2dc")
f_pp = F(num_format='+0.00" pp";-0.00" pp"', border=1, border_color="#e3e2dc")
f_dec = F(num_format="0.0000", border=1, border_color="#e3e2dc")
f_sci = F(num_format="0.00E+00", border=1, border_color="#e3e2dc")
f_input = F(num_format="0.00", font_color="#0000FF", bg_color="#FFFF00", border=1, border_color="#e3e2dc", bold=True)
f_result = F(bold=True, border=1, border_color="#e3e2dc", bg_color="#e7f3ec", font_color="#0b5d2c")
f_link_pct = F(num_format="0.00%", font_color="#008000", border=1, border_color="#e3e2dc")
f_kpi_lbl = F(font_color="#52514e", font_size=9, align="center", bg_color="#f4f3ef", top=1, left=1, right=1, border_color="#d6d5cf")
f_kpi_pct = F(num_format="0.00%", bold=True, font_size=18, align="center", bg_color="#f4f3ef", bottom=1, left=1, right=1, border_color="#d6d5cf")
f_kpi_rel = F(num_format="+0%", bold=True, font_size=18, align="center", bg_color="#f4f3ef", bottom=1, left=1, right=1, border_color="#d6d5cf", font_color="#0b5d2c")
f_kpi_p = F(num_format="0.0E+00", bold=True, font_size=18, align="center", bg_color="#f4f3ef", bottom=1, left=1, right=1, border_color="#d6d5cf")
f_kpi_int = F(num_format="#,##0", bold=True, font_size=18, align="center", bg_color="#f4f3ef", bottom=1, left=1, right=1, border_color="#d6d5cf")
f_take = F(bold=True, font_size=11, text_wrap=True, valign="top", bg_color="#eef4fb", border=1, border_color="#c9d9ee")
f_data_hdr = F(bold=True, bg_color="#1f3a5f", font_color="white")
f_data = F()

# ---------------------------------------------------------------- python reference values
g = df.groupby("test_group")
n = g.size(); conv = g["converted"].sum(); cr = conv / n
nA, nB, xA, xB = n["ad"], n["psa"], conv["ad"], conv["psa"]
pA, pB = xA / nA, xB / nB
diff = pA - pB
pooled = (xA + xB) / (nA + nB)
se_pooled = np.sqrt(pooled * (1 - pooled) * (1 / nA + 1 / nB))
z = diff / se_pooled
pval = 2 * (1 - stats.norm.cdf(abs(z)))
se_un = np.sqrt(pA * (1 - pA) / nA + pB * (1 - pB) / nB)
zc = stats.norm.ppf(1 - ALPHA / 2)
obs = np.array([[xA, xB], [nA - xA, nB - xB]])
chi_p = stats.chi2_contingency(obs, correction=False)[1]
exp = obs.sum(1, keepdims=True) * obs.sum(0, keepdims=True) / obs.sum()

def seg(col, keys):
    t = df.groupby([col, "test_group"])["converted"].agg(["count", "sum"]).unstack()
    return t.reindex(keys)

seg_bucket, seg_day, seg_hour = seg("ads_bucket", BUCKETS), seg("most_ads_day", DAYS), seg("most_ads_hour", list(range(24)))

# ---------------------------------------------------------------- sheets (created in tab order)
ws_start = wb.add_worksheet("Start Here")
ws_dash = wb.add_worksheet("Dashboard")
ws_ab = wb.add_worksheet("AB_Test")
ws_seg = wb.add_worksheet("Segments")
ws_dq = wb.add_worksheet("Data_Quality")
ws_data = wb.add_worksheet("Data")

# ---------------------------------------------------------------- Data
cols = ["user_id", "test_group", "converted", "total_ads", "ads_bucket", "most_ads_day", "most_ads_hour"]
for c, name in enumerate(cols):
    ws_data.write(0, c, name, f_data_hdr)
for c, name in enumerate(cols):
    ws_data.write_column(1, c, df[name].tolist(), f_data)
ws_data.set_column(0, 0, 11); ws_data.set_column(1, 4, 12); ws_data.set_column(5, 6, 14)
ws_data.freeze_panes(1, 0)
ws_data.autofilter(0, 0, LAST - 1, len(cols) - 1)

for name, col in [("rng_user", "A"), ("rng_group", "B"), ("rng_conv", "C"), ("rng_ads", "D"),
                  ("rng_bucket", "E"), ("rng_day", "F"), ("rng_hour", "G")]:
    wb.define_name(name, f"=Data!${col}$2:${col}${LAST}")

# ---------------------------------------------------------------- AB_Test
ws = ws_ab
ws.set_column("A:A", 44); ws.set_column("B:D", 17); ws.set_column("E:E", 3); ws.set_column("F:F", 58)
ws.write("A1", "A/B test: do ads increase conversion vs a public-service ad (PSA)?", f_title)
ws.write("A2", "Treatment = saw the company's ad · Control = saw a PSA in the same slot · Outcome = converted (1/0)", f_sub)

ws.write("A4", "1. Results by group", f_h2)
ws.write_row("A5", ["Metric", "Ad (treatment)", "PSA (control)"], f_hdr)
ws.write("A6", "Users", f_lbl); ws.write_formula("B6", '=COUNTIF(rng_group,"ad")', f_int, nA); ws.write_formula("C6", '=COUNTIF(rng_group,"psa")', f_int, nB)
ws.write("A7", "Conversions", f_lbl); ws.write_formula("B7", '=COUNTIFS(rng_group,"ad",rng_conv,1)', f_int, xA); ws.write_formula("C7", '=COUNTIFS(rng_group,"psa",rng_conv,1)', f_int, xB)
ws.write("A8", "Conversion rate", f_lbl_b); ws.write_formula("B8", "=B7/B6", f_pct, pA); ws.write_formula("C8", "=C7/C6", f_pct, pB)
ws.write("A9", "Share of users", f_lbl); ws.write_formula("B9", "=B6/(B6+C6)", f_pct1, nA / N); ws.write_formula("C9", "=C6/(B6+C6)", f_pct1, nB / N)
ws.write("F6", "Each count is a COUNTIF/COUNTIFS over the Data sheet (named ranges rng_group, rng_conv).", f_note)
ws.write("F9", "96/4 split: the test deliberately kept the control group small. Unequal groups are fine for a z-test; the small control is why its estimate is less precise.", f_note)

ws.write("A11", "2. Two-proportion z-test", f_h2)
ws.write_row("A12", ["Item", "Value", ""], f_hdr)
ws.write("A13", "Significance level α  (input)", f_lbl_b); ws.write_number("B13", ALPHA, f_input)
ws.write("F13", "Blue on yellow = input you can change. Everything else is a formula.", f_note)
ws.write("A14", "Absolute lift (Ad − PSA)", f_lbl); ws.write_formula("B14", "=(B8-C8)*100", f_pp, diff * 100)
ws.write("F14", "In percentage points.", f_note)
ws.write("A15", "Relative lift", f_lbl_b); ws.write_formula("B15", "=(B8-C8)/C8", f_pct1, diff / pB)
ws.write("A16", "Pooled conversion rate", f_lbl); ws.write_formula("B16", "=(B7+C7)/(B6+C6)", f_pct, pooled)
ws.write("A17", "Standard error (pooled)", f_lbl); ws.write_formula("B17", "=SQRT(B16*(1-B16)*(1/B6+1/C6))", f_dec, se_pooled)
ws.write("A18", "z-statistic", f_lbl); ws.write_formula("B18", "=(B8-C8)/B17", F(num_format="0.00", border=1, border_color="#e3e2dc"), z)
ws.write("A19", "p-value (two-sided)", f_lbl_b); ws.write_formula("B19", "=2*(1-NORMSDIST(ABS(B18)))", f_sci, pval)
ws.write("F19", "Scientific notation: 1.7E-13 = 0.00000000000017. Far below α, so the difference is not chance.", f_note)
ws.write("A20", "Decision", f_lbl_b)
ws.write_formula("B20", '=IF(B19<B13,"Significant: reject H0","Not significant")', f_result,
                 "Significant: reject H0" if pval < ALPHA else "Not significant")
ws.write("F20", "H0: ads and PSA convert at the same rate.", f_note)

ws.write("A22", "3. Confidence interval for the lift", f_h2)
ws.write_row("A23", ["Item", "Value", ""], f_hdr)
ws.write("A24", "Standard error (unpooled)", f_lbl); ws.write_formula("B24", "=SQRT(B8*(1-B8)/B6+C8*(1-C8)/C6)", f_dec, se_un)
ws.write("A25", "Critical z for chosen α", f_lbl); ws.write_formula("B25", "=NORMSINV(1-B13/2)", F(num_format="0.000", border=1, border_color="#e3e2dc"), zc)
ws.write("A26", "Lift: lower bound", f_lbl); ws.write_formula("B26", "=((B8-C8)-B25*B24)*100", f_pp, (diff - zc * se_un) * 100)
ws.write("A27", "Lift: upper bound", f_lbl); ws.write_formula("B27", "=((B8-C8)+B25*B24)*100", f_pp, (diff + zc * se_un) * 100)
ws.write("F26", "The whole interval is above zero, so the lift is real — but its width shows the uncertainty from the small control group.", f_note)

ws.write("A29", "4. Cross-check: chi-square test of independence", f_h2)
ws.write_row("A30", ["Observed", "Ad", "PSA", "Total"], f_hdr)
ws.write("A31", "Converted", f_lbl); ws.write_formula("B31", "=B7", f_int, xA); ws.write_formula("C31", "=C7", f_int, xB); ws.write_formula("D31", "=B31+C31", f_int, xA + xB)
ws.write("A32", "Not converted", f_lbl); ws.write_formula("B32", "=B6-B7", f_int, nA - xA); ws.write_formula("C32", "=C6-C7", f_int, nB - xB); ws.write_formula("D32", "=B32+C32", f_int, N - xA - xB)
ws.write("A33", "Total", f_lbl_b); ws.write_formula("B33", "=B31+B32", f_int, nA); ws.write_formula("C33", "=C31+C32", f_int, nB); ws.write_formula("D33", "=D31+D32", f_int, N)
ws.write_row("A35", ["Expected (if no effect)", "Ad", "PSA", ""], f_hdr)
ws.write("A36", "Converted", f_lbl); ws.write_formula("B36", "=$D31*B$33/$D$33", f_dec, exp[0, 0]); ws.write_formula("C36", "=$D31*C$33/$D$33", f_dec, exp[0, 1])
ws.write("A37", "Not converted", f_lbl); ws.write_formula("B37", "=$D32*B$33/$D$33", f_dec, exp[1, 0]); ws.write_formula("C37", "=$D32*C$33/$D$33", f_dec, exp[1, 1])
ws.write("A38", "Chi-square p-value", f_lbl_b); ws.write_formula("B38", "=CHITEST(B31:C32,B36:C37)", f_sci, chi_p)
ws.write("F38", "Agrees with the z-test (for a 2×2 table, chi-square = z²).", f_note)

ws.write("A40", "5. Business impact", f_h2)
ws.write_row("A41", ["Item", "Value", ""], f_hdr)
ws.write("A42", "Extra conversions caused by ads", f_lbl_b); ws.write_formula("B42", "=(B8-C8)*B6", f_int, diff * nA)
ws.write("F42", "Ad-group users × lift: conversions that would not have happened with a PSA.", f_note)
ws.write("A43", "Average value per conversion  (input)", f_lbl_b); ws.write_number("B43", 0, F(num_format="$#,##0.00", font_color="#0000FF", bg_color="#FFFF00", border=1, border_color="#e3e2dc", bold=True))
ws.write("A44", "Incremental revenue", f_lbl); ws.write_formula("B44", "=B42*B43", F(num_format="$#,##0", border=1, border_color="#e3e2dc"), 0)
ws.write("F43", "Not in the dataset — enter the real average order value to size the campaign's return.", f_note)
ws.freeze_panes(3, 0)

# ---------------------------------------------------------------- Segments
ws = ws_seg
ws.set_column("A:A", 14); ws.set_column("B:K", 12.5)
ws.write("A1", "Conversion by segment", f_title)
ws.write("A2", "Pivot-style summaries built with COUNTIFS. Lift = Ad rate − PSA rate. 'Reliable?' flags segments with fewer than 30 PSA conversions.", f_sub)
seg_hdr = ["Segment", "Ad users", "Ad conv.", "Ad rate", "PSA users", "PSA conv.", "PSA rate", "Lift (pp)", "Relative lift", "Reliable?"]
seg_pos = {}

def seg_table(top, title, keys, rng, table, label_fmt=None):
    ws.write(top, 0, title, f_h2)
    ws.write_row(top + 1, 0, seg_hdr, f_hdr)
    for i, k in enumerate(keys):
        r = top + 2 + i; R = r + 1
        crit = f'"{k}"' if isinstance(k, str) else str(k)
        a_n, a_x = table.loc[k, ("count", "ad")], table.loc[k, ("sum", "ad")]
        b_n, b_x = table.loc[k, ("count", "psa")], table.loc[k, ("sum", "psa")]
        ws.write(r, 0, k if label_fmt is None else label_fmt(k), f_lbl_b)
        ws.write_formula(r, 1, f'=COUNTIFS({rng},A{R},rng_group,"ad")' if isinstance(k, str) else f'=COUNTIFS({rng},{crit},rng_group,"ad")', f_int, a_n)
        ws.write_formula(r, 2, f'=COUNTIFS({rng},A{R},rng_group,"ad",rng_conv,1)' if isinstance(k, str) else f'=COUNTIFS({rng},{crit},rng_group,"ad",rng_conv,1)', f_int, a_x)
        ws.write_formula(r, 3, f"=IFERROR(C{R}/B{R},0)", f_pct, a_x / a_n)
        ws.write_formula(r, 4, f'=COUNTIFS({rng},A{R},rng_group,"psa")' if isinstance(k, str) else f'=COUNTIFS({rng},{crit},rng_group,"psa")', f_int, b_n)
        ws.write_formula(r, 5, f'=COUNTIFS({rng},A{R},rng_group,"psa",rng_conv,1)' if isinstance(k, str) else f'=COUNTIFS({rng},{crit},rng_group,"psa",rng_conv,1)', f_int, b_x)
        ws.write_formula(r, 6, f"=IFERROR(F{R}/E{R},0)", f_pct, b_x / b_n)
        ws.write_formula(r, 7, f"=(D{R}-G{R})*100", f_pp, (a_x / a_n - b_x / b_n) * 100)
        ws.write_formula(r, 8, f'=IFERROR((D{R}-G{R})/G{R},"n/a")', f_pct1, (a_x / a_n - b_x / b_n) / (b_x / b_n) if b_x else "n/a")
        ws.write_formula(r, 9, f'=IF(F{R}>=30,"Yes","Low sample")', f_lbl, "Yes" if b_x >= 30 else "Low sample")
    first, last = top + 3, top + 2 + len(keys)
    seg_pos[title] = (first, last)
    ws.conditional_format(f"H{first}:H{last}", {"type": "data_bar", "bar_color": "#2a78d6", "bar_solid": True})
    ws.conditional_format(f"J{first}:J{last}", {"type": "text", "criteria": "containing", "value": "Low", "format": F(font_color="#b04a10")})
    return last

end1 = seg_table(3, "By ad exposure (total ads seen)", BUCKETS, "rng_bucket", seg_bucket)
ws.write(end1 + 0, 11, "Exposure is what users ended up seeing, not something randomised — read this as correlation.", f_note)
end2 = seg_table(end1 + 2, "By day users saw the most ads", DAYS, "rng_day", seg_day)
end3 = seg_table(end2 + 2, "By hour users saw the most ads", list(range(24)), "rng_hour", seg_hour)
ws.set_column("L:L", 40)
ws.freeze_panes(0, 1)

# ---------------------------------------------------------------- Data_Quality
ws = ws_dq
ws.set_column("A:A", 46); ws.set_column("B:B", 14); ws.set_column("C:C", 62)
ws.write("A1", "Data quality checks", f_title)
ws.write("A2", "Live checks re-run on the Data sheet; the cleaning log records what was done before loading.", f_sub)
ws.write("A4", "Live checks (formulas)", f_h2)
ws.write_row("A5", ["Check", "Result", "Expected / meaning"], f_hdr)
checks = [
    ("Rows in Data", "=ROWS(rng_user)", N, "588,101 users"),
    ("Blank cells (all 7 columns)", "=COUNTBLANK(rng_user)+COUNTBLANK(rng_group)+COUNTBLANK(rng_conv)+COUNTBLANK(rng_ads)+COUNTBLANK(rng_bucket)+COUNTBLANK(rng_day)+COUNTBLANK(rng_hour)", 0, "0"),
    ("test_group not 'ad' or 'psa'", '=ROWS(rng_group)-COUNTIF(rng_group,"ad")-COUNTIF(rng_group,"psa")', 0, "0"),
    ("converted not 0 or 1", "=ROWS(rng_conv)-COUNTIF(rng_conv,0)-COUNTIF(rng_conv,1)", 0, "0"),
    ("total_ads below 1", '=COUNTIF(rng_ads,"<1")', 0, "0"),
    ("most_ads_hour outside 0–23", '=COUNTIF(rng_hour,"<0")+COUNTIF(rng_hour,">23")', 0, "0"),
    ("most_ads_day not a weekday name", '=ROWS(rng_day)-SUMPRODUCT(COUNTIF(rng_day,{"Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"}))', 0, "0"),
    ("Users in an exposure bucket", '=SUMPRODUCT(COUNTIF(rng_bucket,{"1-9","10-24","25-49","50-99","100+"}))', N, "Should equal Rows in Data"),
    ("Median ads seen", "=MEDIAN(rng_ads)", float(df["total_ads"].median()), "Typical exposure"),
    ("99th percentile of ads seen", "=PERCENTILE(rng_ads,0.99)", float(np.percentile(df["total_ads"], 99)), "Heavy-user threshold"),
    ("Max ads seen by one user", "=MAX(rng_ads)", int(df["total_ads"].max()), "Extreme but plausible (bots or very heavy users) — kept"),
]
for i, (lbl, formula, val, note) in enumerate(checks):
    r = 5 + i
    ws.write(r, 0, lbl, f_lbl)
    ws.write_formula(r, 1, formula, f_int, val)
    ws.write(r, 2, note, f_note)
first, last = 7, 5 + len(checks)
ws.conditional_format(f"B7:B12", {"type": "cell", "criteria": ">", "value": 0, "format": F(bg_color="#fde2d6", font_color="#9c2b00")})
ws.conditional_format(f"B7:B12", {"type": "cell", "criteria": "==", "value": 0, "format": F(bg_color="#e7f3ec", font_color="#0b5d2c")})

top = 5 + len(checks) + 2
ws.write(top, 0, "Cleaning log (from src/clean_data.py)", f_h2)
ws.write_row(top + 1, 0, ["Step / check", "Result", "Action"], f_hdr)
for i, row in log.iterrows():
    ws.write(top + 2 + i, 0, row["check"], f_lbl)
    ws.write_number(top + 2 + i, 1, row["result"], f_int)
    ws.write(top + 2 + i, 2, "" if pd.isna(row["action"]) else row["action"], f_note)
ws.write(top + 3 + len(log), 0, "Duplicate user IDs are checked in Python: COUNTIF over 588K rows against itself is too slow for Excel.", f_note)

# ---------------------------------------------------------------- Dashboard
ws = ws_dash
ws.hide_gridlines(2)
ws.set_column("A:A", 2); ws.set_column("B:K", 13)
ws.write("B1", "Marketing A/B test — results dashboard", f_title)
ws.write("B2", f"588,101 users · Ad vs public-service ad (PSA) · all figures link to the AB_Test and Segments sheets", f_sub)
kpis = [
    ("B", "Ad conversion", "=AB_Test!B8", f_kpi_pct, pA),
    ("D", "PSA conversion", "=AB_Test!C8", f_kpi_pct, pB),
    ("F", "Relative lift", "=AB_Test!B15", f_kpi_rel, diff / pB),
    ("H", "p-value", "=AB_Test!B19", f_kpi_p, pval),
    ("J", "Extra conversions", "=AB_Test!B42", f_kpi_int, diff * nA),
]
for col, lbl, formula, fmt, val in kpis:
    nxt = chr(ord(col) + 1)
    ws.merge_range(f"{col}4:{nxt}4", lbl, f_kpi_lbl)
    ws.merge_range(f"{col}5:{nxt}5", "", fmt)
    ws.write_formula(f"{col}5", formula, fmt, val)
ws.set_row(4, 34)
take_val = (f"Ads lifted conversion from {pB:.2%} to {pA:.2%} (+{diff / pB:.0%} relative, p < 0.001). "
            f"Roll out the ad campaign; keep a small PSA holdout to keep measuring.")
ws.merge_range("B7:K8", "", f_take)
ws.write_formula("B7", '="Ads lifted conversion from "&TEXT(AB_Test!C8,"0.00%")&" to "&TEXT(AB_Test!B8,"0.00%")&" (+"&TEXT(AB_Test!B15,"0%")&" relative, "&IF(AB_Test!B19<0.001,"p < 0.001","p = "&TEXT(AB_Test!B19,"0.000"))&"). "&IF(AB_Test!B19<AB_Test!B13,"Roll out the ad campaign; keep a small PSA holdout to keep measuring.","Not significant: do not roll out on this evidence.")',
                 f_take, take_val)
ws.set_row(6, 22); ws.set_row(7, 22)

def chart_style(ch, title, y_title=None):
    ch.set_title({"name": title, "name_font": {"name": FONT, "size": 11, "bold": True}})
    ch.set_legend({"position": "bottom", "font": {"name": FONT, "size": 9}})
    ch.set_chartarea({"border": {"none": True}})
    ch.set_plotarea({"border": {"none": True}})
    ch.set_y_axis({"num_format": "0.0%", "major_gridlines": {"visible": True, "line": {"color": "#ecebe7"}},
                   "num_font": {"name": FONT, "size": 9}, "line": {"none": True},
                   **({"name": y_title, "name_font": {"name": FONT, "size": 9, "bold": False}} if y_title else {})})
    ch.set_x_axis({"num_font": {"name": FONT, "size": 9}, "line": {"color": "#d6d5cf"}})

c1 = wb.add_chart({"type": "column"})
c1.add_series({"name": "Conversion rate", "categories": "=AB_Test!$B$5:$C$5", "values": "=AB_Test!$B$8:$C$8",
               "points": [{"fill": {"color": "#2a78d6"}}, {"fill": {"color": "#b8b6ae"}}],
               "data_labels": {"value": True, "num_format": "0.00%", "font": {"name": FONT, "size": 9}},
               "gap": 120})
chart_style(c1, "Conversion rate by group"); c1.set_legend({"none": True})
ws.insert_chart("B10", c1, {"x_scale": 0.9, "y_scale": 1.0})

b1, b2 = seg_pos["By ad exposure (total ads seen)"]
c2 = wb.add_chart({"type": "column"})
c2.add_series({"name": "Ad", "categories": f"=Segments!$A${b1}:$A${b2}", "values": f"=Segments!$D${b1}:$D${b2}", "fill": {"color": "#2a78d6"}, "gap": 80})
c2.add_series({"name": "PSA", "categories": f"=Segments!$A${b1}:$A${b2}", "values": f"=Segments!$G${b1}:$G${b2}", "fill": {"color": "#b8b6ae"}})
chart_style(c2, "Conversion rate by ads seen"); c2.set_x_axis({"name": "Total ads seen", "name_font": {"name": FONT, "size": 9, "bold": False}, "num_font": {"name": FONT, "size": 9}})
ws.insert_chart("G10", c2, {"x_scale": 0.9, "y_scale": 1.0})

d1, d2 = seg_pos["By day users saw the most ads"]
c3 = wb.add_chart({"type": "column"})
c3.add_series({"name": "Ad", "categories": f"=Segments!$A${d1}:$A${d2}", "values": f"=Segments!$D${d1}:$D${d2}", "fill": {"color": "#2a78d6"}, "gap": 80})
c3.add_series({"name": "PSA", "categories": f"=Segments!$A${d1}:$A${d2}", "values": f"=Segments!$G${d1}:$G${d2}", "fill": {"color": "#b8b6ae"}})
chart_style(c3, "Conversion rate by peak ad day")
ws.insert_chart("B26", c3, {"x_scale": 0.9, "y_scale": 1.0})

h1, h2 = seg_pos["By hour users saw the most ads"]
c4 = wb.add_chart({"type": "line"})
c4.add_series({"name": "Ad", "categories": f"=Segments!$A${h1}:$A${h2}", "values": f"=Segments!$D${h1}:$D${h2}", "line": {"color": "#2a78d6", "width": 2}})
c4.add_series({"name": "PSA", "categories": f"=Segments!$A${h1}:$A${h2}", "values": f"=Segments!$G${h1}:$G${h2}", "line": {"color": "#b8b6ae", "width": 1.5, "dash_type": "dash"}})
chart_style(c4, "Conversion rate by peak ad hour"); c4.set_x_axis({"name": "Hour of day", "name_font": {"name": FONT, "size": 9, "bold": False}, "num_font": {"name": FONT, "size": 9}, "interval_unit": 2})
ws.insert_chart("G26", c4, {"x_scale": 0.9, "y_scale": 1.0})
ws.merge_range("B42:K42", "PSA lines by hour are based on ~1,000 users each, so hour-level PSA rates are noisy — see 'Reliable?' on the Segments sheet.", f_note)

# ---------------------------------------------------------------- Start Here
ws = ws_start
ws.hide_gridlines(2)
ws.set_column("A:A", 2); ws.set_column("B:B", 22); ws.set_column("C:C", 90)
ws.write("B1", "Marketing A/B Test Analysis", f_title)
ws.write("B2", "Excel · statistics · business recommendation", f_sub)
rows = [
    ("Business question", "A company showed its ad to most users and a public-service ad (PSA) to a small control group. Did the ad actually cause more conversions, by how much, and is the result trustworthy?"),
    ("Data", "Kaggle 'Marketing A/B Testing' dataset: 588,101 users — test group, converted (yes/no), total ads seen, day and hour they saw the most ads."),
    ("Answer", take_val),
    ("", ""),
    ("Sheet guide", ""),
    ("Dashboard", "KPI tiles, the headline finding, and four charts. Everything links to the analysis sheets."),
    ("AB_Test", "Conversion by group, two-proportion z-test, 95% confidence interval, chi-square cross-check, business impact."),
    ("Segments", "Pivot-style COUNTIFS tables: conversion and lift by ad exposure, day and hour, with small-sample flags."),
    ("Data_Quality", "Live validation formulas on the raw data plus the cleaning log."),
    ("Data", "Cleaned data — one row per user. Named ranges: rng_group, rng_conv, rng_ads, rng_bucket, rng_day, rng_hour."),
    ("", ""),
    ("Colour legend", "Blue text on yellow = input you can change (significance level, value per conversion). Green = link to another sheet. Black = formula."),
    ("Recalculation", "All results are formulas. Change α on AB_Test and the decision, interval and dashboard text update."),
]
for i, (a, b) in enumerate(rows):
    r = 3 + i
    ws.write(r, 1, a, F(bold=True, valign="top"))
    if a == "Answer":
        ws.write_formula(r, 2, "=Dashboard!B7", f_txt, b)
    else:
        ws.write(r, 2, b, f_txt)
    if len(b) > 95:
        ws.set_row(r, 28)
ws.activate()

# print setup: dashboard/analysis sheets fit to page width; Data prints only its first rows
for sheet in (ws_start, ws_dash, ws_ab, ws_seg, ws_dq):
    sheet.set_landscape(); sheet.fit_to_pages(1, 1 if sheet in (ws_dash, ws_ab, ws_start) else 0); sheet.set_paper(1)
ws_data.print_area("A1:G60")

wb.close()
print(f"wrote {OUT} ({OUT.stat().st_size/1e6:.1f} MB)")
print(f"ad {pA:.4%}  psa {pB:.4%}  lift {diff*100:.3f}pp ({diff/pB:.1%})  z={z:.2f}  p={pval:.3g}  CI=[{(diff-zc*se_un)*100:.3f}, {(diff+zc*se_un)*100:.3f}]pp  chi p={chi_p:.3g}  extra={diff*nA:,.0f}")

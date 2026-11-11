"""
Compare the cached values xlsxwriter stored (Python-computed) with the values
LibreOffice/Excel computes from the formulas.

    python src/verify_workbook.py <original.xlsx> <recalculated_copy.xlsx>

Recalculate the copy first, e.g. open it in Excel and save, or with LibreOffice:
    soffice --headless --convert-to xlsx --outdir recalc/ excel/ab_test_analysis.xlsx
"""
import sys

from openpyxl import load_workbook

orig = load_workbook(sys.argv[1], data_only=True, read_only=True)
calc = load_workbook(sys.argv[2], data_only=True, read_only=True)
formulas = load_workbook(sys.argv[1], read_only=True)

checked = mismatched = 0
for name in ["Dashboard", "AB_Test", "Segments", "Data_Quality", "Start Here"]:
    fo = {(c.row, c.column): c.value for row in formulas[name].iter_rows() for c in row if hasattr(c, "column")}
    a = {(c.row, c.column): c.value for row in orig[name].iter_rows() for c in row if hasattr(c, "column")}
    b = {(c.row, c.column): c.value for row in calc[name].iter_rows() for c in row if hasattr(c, "column")}
    for key, f in fo.items():
        if not (isinstance(f, str) and f.startswith("=")):
            continue
        checked += 1
        x, y = a.get(key), b.get(key)
        same = (x == y) if not (isinstance(x, (int, float)) and isinstance(y, (int, float))) \
            else abs(x - y) <= 1e-9 * max(1, abs(x), abs(y))
        if not same:
            mismatched += 1
            print(f"{name}!R{key[0]}C{key[1]}: python={x!r}  excel={y!r}  formula={f}")
print(f"{checked} formulas checked, {mismatched} mismatches")

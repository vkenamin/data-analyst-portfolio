"""
Run every "-- @name:" query in sql/04_analysis.sql and save each result to
results/<name>.csv, using the psql command-line tool (installed with PostgreSQL).

Usage (from the project folder, with psql on PATH):
    python scripts/export_results.py

Connection settings come from the standard PG environment variables
(PGUSER, PGPASSWORD, PGHOST, PGPORT); the database defaults to "portfolio".
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL_FILE = ROOT / "sql" / "04_analysis.sql"
OUT_DIR = ROOT / "results"
DB = os.getenv("PGDATABASE", "portfolio")


def split_named_queries(sql_text: str) -> dict[str, str]:
    """Return {name: sql} for each block that starts with '-- @name: <name>'."""
    parts = re.split(r"^-- @name:\s*(\w+)\s*$", sql_text, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip().rstrip(";") for i in range(1, len(parts), 2)}


def main() -> None:
    psql = shutil.which("psql")
    if not psql:
        sys.exit("psql not found. Add PostgreSQL's bin folder to PATH, e.g. C:\\Program Files\\PostgreSQL\\18\\bin")

    env = dict(os.environ, PGOPTIONS="-c search_path=olist", PGCLIENTENCODING="UTF8")
    OUT_DIR.mkdir(exist_ok=True)
    queries = split_named_queries(SQL_FILE.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        for name, query in queries.items():
            qfile = Path(tmp) / f"{name}.sql"
            qfile.write_text(query + ";\n", encoding="utf-8")
            out = OUT_DIR / f"{name}.csv"
            result = subprocess.run(
                [psql, "-X", "-q", "--csv", "-v", "ON_ERROR_STOP=1",
                 "-d", DB, "-f", str(qfile), "-o", str(out)],
                env=env, capture_output=True, text=True, encoding="utf-8",
            )
            if result.returncode != 0:
                sys.exit(f"{name} failed:\n{result.stderr}")
            rows = max(sum(1 for _ in out.open(encoding="utf-8")) - 1, 0)
            print(f"{name:<28} {rows:>5} rows")


if __name__ == "__main__":
    main()

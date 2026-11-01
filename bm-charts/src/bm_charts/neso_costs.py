"""NESO's total balancing costs by calendar year: ``uv run neso-costs``.

NESO publishes its daily balancing costs (the costs recovered through BSUoS)
on its data portal as one CSV per financial year (April to March). This
downloads every file, stitches the days together and re-cuts them into
calendar years, so the annual costs slide can use January to December totals
instead of NESO's financial years.

Unlike the Elexon BM data, these are NESO's *total* balancing costs: the BM
plus trades, reserve, response, constraint contracts and other services. The
files are small (one row per day or per settlement period) and are cached in
``data/neso/``; the latest year's file is always refetched.
"""

from __future__ import annotations

import argparse
import io
import re
from datetime import datetime
from pathlib import Path

import httpx
import polars as pl

DATASET_ID = "d13d78fc-60d9-4f4d-87b6-e25a20f669c0"  # Daily Balancing Services Use of System (BSUoS) Cost Data
API = "https://api.neso.energy/api/3/action"
SOURCE = "Source: NESO Data Portal, Daily Balancing Services Use of System (BSUoS) Cost Data"

DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%d-%b-%Y", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S")
NON_COST = re.compile(r"date|period|sp\b|settlement|time|^id$|_id$", re.I)
TOTAL = re.compile(r"total|^cost$|^costs$|bsuos", re.I)


def list_resources(client: httpx.Client) -> list[dict]:
    """The financial-year CSVs in the dataset, oldest first."""
    r = client.get(f"{API}/package_show", params={"id": DATASET_ID})
    r.raise_for_status()
    out = []
    for res in r.json()["result"]["resources"]:
        name = res.get("name") or ""
        fy = re.search(r"(20\d\d)\s*[-/–]\s*(20\d\d|\d\d)", name)
        if (res.get("format") or "").lower() == "csv" and fy:
            out.append({"name": name, "url": res["url"], "fy_start": int(fy.group(1))})
    return sorted(out, key=lambda x: x["fy_start"])


def fetch(cache: Path, transport=None) -> list[tuple[str, bytes]]:
    cache.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120, follow_redirects=True, transport=transport) as client:
        resources = list_resources(client)
        if not resources:
            raise RuntimeError(f"No financial-year CSVs found in NESO dataset {DATASET_ID}")
        latest = resources[-1]["fy_start"]
        files = []
        for res in resources:
            path = cache / f"fy{res['fy_start']}.csv"
            if not path.exists() or res["fy_start"] >= latest - 1:
                print(f"  fetching {res['name']}")
                r = client.get(res["url"])
                r.raise_for_status()
                path.write_bytes(r.content)
            files.append((res["name"], path.read_bytes()))
    return files


def _parse_dates(col: pl.Series) -> pl.Series:
    s = col.cast(pl.Utf8).str.strip_chars()
    for fmt in DATE_FORMATS:
        parsed = s.str.strptime(pl.Datetime, fmt, strict=False)
        if parsed.null_count() <= len(s) * 0.01:
            return parsed.dt.date()
    raise ValueError(f"Could not parse dates in column {col.name!r}, e.g. {s[0]!r}")


def to_daily(files: list[tuple[str, bytes]]) -> pl.DataFrame:
    """One row per day, one column per cost category (£), plus ``total``."""
    frames = []
    for name, raw in files:
        df = pl.read_csv(io.BytesIO(raw), infer_schema_length=0)  # all strings; cast below
        df = df.rename({c: c.strip() for c in df.columns})
        date_col = next((c for c in df.columns if "date" in c.lower()), None)
        if date_col is None:
            raise ValueError(f"{name}: no date column in {df.columns}")
        costs = {}
        for c in df.columns:
            if NON_COST.search(c):
                continue
            v = df[c].str.replace_all(r"[£,\s]", "").cast(pl.Float64, strict=False)
            if v.null_count() < len(v) * 0.5:
                costs[c] = v.fill_null(0)
        totals = [c for c in costs if TOTAL.search(c)]
        frame = pl.DataFrame({"date": _parse_dates(df[date_col]), **costs})
        if totals:
            frame = frame.rename({totals[0]: "total"}).drop(totals[1:])
        else:
            frame = frame.with_columns(pl.sum_horizontal(list(costs)).alias("total"))
        # Settlement-period rows sum to days.
        cats = [c for c in frame.columns if c != "date"]
        frames.append(frame.group_by("date").agg([pl.col(c).sum() for c in cats]))
    # Files come oldest first; if two overlap, keep the newer file's copy of a day.
    daily = pl.concat(frames, how="diagonal_relaxed").fill_null(0)
    return daily.unique("date", keep="last", maintain_order=True).sort("date")


def by_year(daily: pl.DataFrame, financial: bool = False) -> pl.DataFrame:
    """Totals in £m per calendar year (or financial year, April start, for checking
    against NESO's annual reports), with how many days each year has."""
    if financial:
        key = (pl.col("date").dt.year() - (pl.col("date").dt.month() < 4).cast(pl.Int32))
        label = key.cast(pl.Utf8) + "/" + ((key + 1) % 100).cast(pl.Utf8).str.zfill(2)
    else:
        label = pl.col("date").dt.year().cast(pl.Utf8)
    cats = [c for c in daily.columns if c != "date"]
    return (
        daily.with_columns(label.alias("year"))
        .group_by("year")
        .agg(pl.len().alias("days"), pl.col("date").min().alias("first_day"),
             pl.col("date").max().alias("last_day"), *[(pl.col(c).sum() / 1e6).round(1) for c in cats])
        .rename({c: f"{c}_£m" for c in cats})
        .sort("year")
    )


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="NESO daily balancing costs, totalled by calendar year.")
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--out-dir", type=Path, default=Path("output"))
    args = p.parse_args(argv)

    print("Fetching NESO daily balancing costs")
    daily = to_daily(fetch(args.data_dir / "neso"))
    full = args.out_dir / "data" / "full"
    full.mkdir(parents=True, exist_ok=True)
    daily.write_csv(full / "neso_daily_balancing_costs.csv")
    cy = by_year(daily)
    fy = by_year(daily, financial=True)
    cy.write_csv(args.out_dir / "data" / "06_neso_annual_balancing_costs_calendar_year.csv")
    fy.write_csv(full / "neso_annual_balancing_costs_financial_year.csv")
    with pl.Config(tbl_rows=30, tbl_cols=30, tbl_width_chars=200):
        print("\nCalendar-year totals (£m):")
        print(cy)
        print("\nFinancial-year totals (£m), to check against NESO's annual reports:")
        print(fy)
    print(f"\nwrote {args.out_dir / 'data' / '06_neso_annual_balancing_costs_calendar_year.csv'}")
    print(f"Data runs {daily['date'].min()} to {daily['date'].max()} ({datetime.now():%d %b %Y} run)")


if __name__ == "__main__":
    main()

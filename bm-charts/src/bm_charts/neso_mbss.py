"""NESO's total balancing costs on the MBSS basis, by year: ``uv run neso-mbss``.

The Monthly Balancing Services Summary (MBSS) is the series behind NESO's
headline annual costs. Its data portal dataset refuses anonymous access, so the
files come from the links on NESO's public balancing costs page:

- one zip per financial year, 2019/20 to 2024/25 holding monthly workbooks (the
  March one covers the whole year) and 2025/26 holding CSVs;
- rolling CSVs of the latest 12 months, which take over where the zips stop.

MBSS starts in April 2019 here. Earlier months are rebuilt as daily BSUoS costs
(``neso_costs``, BM and trades only) plus the MBSS daily ancillary services file,
which goes back to April 2017. That sum lands within about 2% of MBSS for every
year they overlap, and the ``source`` column marks the months it supplies.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import re
import zipfile
from datetime import date, datetime
from pathlib import Path

import httpx
import openpyxl
import polars as pl

from bm_charts import neso_costs

PAGE = "https://www.neso.energy/industry-information/balancing-costs"
SOURCE = "Source: NESO, Monthly Balancing Services Summary (MBSS)"

CATEGORIES = [
    "Energy Imbalance", "Operating Reserve", "STOR", "Constraints", "Negative Reserve", "Fast Reserve",
    "Response", "Other Reserve", "Reactive", "Black Start", "Minor Components",
]
# The CSVs split out what the workbooks call Constraints, and rename two categories.
CSV_CONSTRAINTS = {
    "Constraints - England & Wales", "Constraints - Cheviot", "Constraints - Scotland",
    "Constraints - Ancillary Services", "ROCOF", "Constrained Sterilised HR",
}
CSV_RENAME = {"Restoration": "Black Start"}
THERMAL_LINES = ("BM - Transmission", "Trades - Transmission")
MONTHS = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October November December".split())}

WORKBOOK, CSV_FILE, REBUILT = "MBSS workbook", "MBSS CSV", "Rebuilt: daily BSUoS + ancillary"

# NESO's published figures in £m, to check the totals against.
HEADLINES = {"2021/22": 3100, "2022/23": 4100, "2023/24": 2450, "2024/25": 2700}
HEADLINE_THERMAL = {"2024/25": 1700}


def list_documents(page: str) -> tuple[dict[int, str], dict[str, str]]:
    """Links on the balancing costs page: financial-year zips by start year, and
    the rolling CSVs by name."""
    years, rolling = {}, {}
    for href, text in re.findall(r'<a[^>]+href="([^"]*/document/\d+/download)"[^>]*>(.*?)</a>', page, re.S):
        text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))).strip()
        url = httpx.URL(PAGE).join(href)
        if m := re.fullmatch(r"Monthly Balancing Services Summary \(MBSS\) (20\d\d)/20\d\d", text):
            years[int(m.group(1))] = str(url)
        elif m := re.fullmatch(r"(.+) - Monthly Balancing Services Summary \(MBSS\) Data", text):
            rolling[m.group(1)] = str(url)
    return years, rolling


def fetch(cache: Path, transport=None) -> tuple[dict[int, bytes], dict[str, bytes]]:
    cache.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=300, follow_redirects=True, transport=transport) as client:
        r = client.get(PAGE)
        r.raise_for_status()
        year_urls, rolling_urls = list_documents(r.text)
        if not year_urls or not {"Total Balancing Costs", "Ancillary Services Costs"} <= set(rolling_urls):
            raise RuntimeError(f"MBSS links not found on {PAGE}; has the page changed?")

        def get(url: str, path: Path, refresh: bool) -> bytes:
            if refresh or not path.exists():
                print(f"  fetching {path.name}")
                r = client.get(url)
                r.raise_for_status()
                path.write_bytes(r.content)
            return path.read_bytes()

        latest = max(year_urls)
        years = {y: get(u, cache / f"mbss-{y}.zip", y == latest) for y, u in year_urls.items()}
        rolling = {
            n: get(rolling_urls[n], cache / f"rolling-{n.lower().replace(' ', '-')}.csv", True)
            for n in ("Total Balancing Costs", "Ancillary Services Costs")
        }
    return years, rolling


def _month_start(d: datetime) -> date:
    return date(d.year, d.month, 1)


def parse_workbook(raw: bytes) -> pl.DataFrame:
    """A workbook's 12 months in £m. ``Total categories`` holds the categories,
    and the ``Constraints`` sheet's transmission lines hold the thermal cost."""
    wb = openpyxl.load_workbook(io.BytesIO(raw), data_only=True, read_only=True)
    months, table = None, {}
    for row in wb["Total categories"].iter_rows(values_only=True):
        cells = [c for c in row if c is not None]
        if not cells:
            continue
        if months is None:
            dates = [c for c in cells if isinstance(c, datetime)]
            months = [_month_start(d) for d in dates] if dates else None
        elif cells[0] in (*CATEGORIES, "Total"):
            table[cells[0]] = [float(c) for c in cells[1:]]
            if cells[0] == "Total":  # the volume table repeats these labels further down
                break
    if months is None or set(table) != {*CATEGORIES, "Total"}:
        raise ValueError(f"Unexpected Total categories sheet: months {months}, rows {sorted(table)}")

    thermal = [0.0] * len(months)
    seen = set()
    for row in wb["Constraints"].iter_rows(values_only=True):
        cells = [c for c in row if c is not None]
        label = cells[0].strip() if cells and isinstance(cells[0], str) else None
        if label in THERMAL_LINES and label not in seen:  # first hit is cost, second is volume
            seen.add(label)
            values = [float(c) for c in cells[1:] if isinstance(c, (int, float))]
            if len(values) != len(months):
                raise ValueError(f"{label}: {len(values)} values for {len(months)} months")
            thermal = [t + v for t, v in zip(thermal, values)]
    if seen != set(THERMAL_LINES):
        raise ValueError(f"Thermal lines missing from Constraints sheet, found {seen}")

    return pl.DataFrame({
        "month": months, "source": [WORKBOOK] * len(months),
        **{c: table[c] for c in CATEGORIES},
        "thermal_constraints": thermal, "total": table["Total"],
    })


def parse_total_csv(raw: bytes) -> pl.DataFrame:
    """A Total Balancing Costs CSV in £m. These don't separate thermal from
    voltage, so ``thermal_constraints`` stays empty."""
    rows = []
    for rec in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        out = dict.fromkeys(CATEGORIES, 0.0)
        for col, value in rec.items():
            name = col.strip().rstrip("*^")
            if name in ("Year", "Month"):
                continue
            target = "Constraints" if name in CSV_CONSTRAINTS else CSV_RENAME.get(name, name)
            if target not in out:
                raise ValueError(f"Unknown MBSS CSV column {col!r}")
            out[target] += float(value or 0) / 1e6
        rows.append({
            "month": date(int(rec["Year"]), MONTHS[rec["Month"].strip()], 1), "source": CSV_FILE,
            **out, "thermal_constraints": None, "total": sum(out.values()),
        })
    return pl.DataFrame(rows, schema_overrides={"thermal_constraints": pl.Float64})


def from_zip(raw: bytes) -> pl.DataFrame:
    """One financial year from its zip: the March workbook, or the CSV if there's no workbook."""
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        march = [n for n in names if n.lower().endswith((".xlsx", ".xlsm")) and "march" in n.lower()]
        if march:
            return parse_workbook(z.read(march[0]))
        total = [n for n in names if n.endswith("Total Balancing Costs.csv")]
        if total:
            return parse_total_csv(z.read(total[0]))
    raise ValueError(f"No March workbook or Total Balancing Costs CSV in zip: {names}")


def rebuild_early(daily: pl.DataFrame, ancillary: bytes, before: date) -> pl.DataFrame:
    """Months before ``before`` from daily BSUoS costs (BM and trades, in £) plus
    daily ancillary services. Only constraints and the total can be separated."""
    bm = (
        daily.filter(pl.col("date") < before)
        .with_columns(pl.col("date").dt.truncate("1mo").alias("month"))
        .group_by("month")
        .agg((pl.col("Constraints").sum() / 1e6).alias("bm_constraints"), (pl.col("total").sum() / 1e6).alias("bm_total"))
    )
    rows = {}
    for rec in csv.DictReader(io.StringIO(ancillary.decode("utf-8-sig"))):
        month = date(int(rec["Year"]), MONTHS[rec["Month"].strip()], 1)
        if month >= before:
            continue
        row = rows.setdefault(month, {"as_constraints": 0.0, "as_total": 0.0})
        for col, value in rec.items():
            if col not in ("Year", "Quarter", "Month", "Day"):
                row["as_total"] += float(value or 0) / 1e6
        row["as_constraints"] += float(rec["Constraints - Ancillary Services"] or 0) / 1e6
    extra = pl.DataFrame([{"month": m, **v} for m, v in rows.items()])
    return bm.join(extra, on="month").select(
        "month", pl.lit(REBUILT).alias("source"),
        (pl.col("bm_constraints") + pl.col("as_constraints")).alias("Constraints"),
        (pl.col("bm_total") + pl.col("as_total")).alias("total"),
    )


def to_monthly(years: dict[int, bytes], rolling: dict[str, bytes], daily: pl.DataFrame) -> pl.DataFrame:
    """One row per month in £m. Rolling CSVs override the zips, as the newest
    reconciled values, and rebuilt months only fill in before MBSS starts."""
    frames = [from_zip(years[y]) for y in sorted(years)]
    frames.append(parse_total_csv(rolling["Total Balancing Costs"]))
    mbss = pl.concat(frames, how="diagonal_relaxed").unique("month", keep="last", maintain_order=True)
    early = rebuild_early(daily, rolling["Ancillary Services Costs"], mbss["month"].min())
    monthly = pl.concat([early, mbss], how="diagonal_relaxed").sort("month")
    columns = ["month", "source", *CATEGORIES, "thermal_constraints", "total"]
    return monthly.select(columns).with_columns(pl.col(pl.Float64).round(3))


def by_year(monthly: pl.DataFrame, financial: bool = False) -> pl.DataFrame:
    """Totals in £m per calendar year (or April-start financial year). Thermal is
    only given for years where every month has it."""
    if financial:
        key = pl.col("month").dt.year() - (pl.col("month").dt.month() < 4).cast(pl.Int32)
        label = key.cast(pl.Utf8) + "/" + ((key + 1) % 100).cast(pl.Utf8).str.zfill(2)
    else:
        label = pl.col("month").dt.year().cast(pl.Utf8)
    return (
        monthly.with_columns(label.alias("year"))
        .group_by("year")
        .agg(
            pl.len().alias("months"),
            pl.col("Constraints").sum().round(1).alias("constraints_£m"),
            (pl.col("total").sum() - pl.col("Constraints").sum()).round(1).alias("other_£m"),
            pl.col("total").sum().round(1).alias("total_£m"),
            pl.when(pl.col("thermal_constraints").null_count() == 0)
            .then(pl.col("thermal_constraints").sum().round(1))
            .alias("thermal_constraints_£m"),
            (pl.col("source") == REBUILT).sum().alias("rebuilt_months"),
        )
        .sort("year")
    )


def validate(fy: pl.DataFrame) -> pl.DataFrame:
    """Financial years against NESO's published figures."""
    rows = []
    for column, published in (("total_£m", HEADLINES), ("thermal_constraints_£m", HEADLINE_THERMAL)):
        for year, value in published.items():
            ours = fy.filter(pl.col("year") == year)[column][0]
            rows.append({"year": year, "measure": column, "published_£m": value, "mbss_£m": ours,
                         "difference_%": round((ours / value - 1) * 100, 1)})
    return pl.DataFrame(rows)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description="NESO MBSS balancing costs, by calendar and financial year.")
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--out-dir", type=Path, default=Path("output"))
    args = p.parse_args(argv)

    print("Fetching NESO MBSS files")
    years, rolling = fetch(args.data_dir / "neso" / "mbss")
    daily = neso_costs.to_daily(neso_costs.fetch(args.data_dir / "neso"))
    monthly = to_monthly(years, rolling, daily)

    full = args.out_dir / "data" / "full"
    full.mkdir(parents=True, exist_ok=True)
    monthly.write_csv(full / "neso_mbss_monthly.csv")
    # 2017 only has nine months, and starts before anything the deck charts.
    cy = by_year(monthly).filter(pl.col("year") >= "2018")
    fy = by_year(monthly, financial=True)
    cy.write_csv(args.out_dir / "data" / "07_neso_mbss_annual_calendar_year.csv")
    fy.write_csv(full / "neso_mbss_annual_financial_year.csv")
    with pl.Config(tbl_rows=30, tbl_cols=30, tbl_width_chars=200):
        print("\nCalendar-year totals (£m):")
        print(cy)
        print("\nFinancial-year totals (£m):")
        print(fy)
        print("\nAgainst NESO's published figures:")
        print(validate(fy))
    print(f"\nwrote {args.out_dir / 'data' / '07_neso_mbss_annual_calendar_year.csv'}")
    print(f"Data runs {monthly['month'].min():%b %Y} to {monthly['month'].max():%b %Y} ({datetime.now():%d %b %Y} run)")


if __name__ == "__main__":
    main()

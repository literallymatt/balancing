"""Command line entry point: ``uv run bm-charts``."""

from __future__ import annotations

import argparse
import asyncio
from datetime import date, timedelta
from pathlib import Path

import matplotlib
import polars as pl

matplotlib.use("Agg")

from . import charts, fetch, report, style, transform  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    yesterday = date.today() - timedelta(days=1)
    p = argparse.ArgumentParser(description="Chart Balancing Mechanism bid and offer costs from Elexon BMRS.")
    p.add_argument("--start", type=date.fromisoformat, default=date(2023, 1, 1),
                   help="First settlement date (default 2023-01-01)")
    p.add_argument("--end", type=date.fromisoformat, default=yesterday,
                   help="Last settlement date (default yesterday)")
    p.add_argument("--event-start", type=date.fromisoformat, default=date(2026, 6, 22),
                   help="First day of the highlighted event (default 2026-06-22, the heatwave)")
    p.add_argument("--event-end", type=date.fromisoformat, default=date(2026, 6, 26))
    p.add_argument("--focus-day", type=date.fromisoformat, default=date(2026, 6, 23),
                   help="Day for the half-hourly chart (default 2026-06-23)")
    p.add_argument("--concurrency", type=int, default=fetch.DEFAULT_CONCURRENCY,
                   help=f"Requests in flight at once (default {fetch.DEFAULT_CONCURRENCY})")
    p.add_argument("--data-dir", type=Path, default=Path("data"))
    p.add_argument("--out-dir", type=Path, default=Path("output"))
    return p.parse_args(argv)


def run(args: argparse.Namespace, transport=None) -> list[charts.Chart]:
    # The event and focus day always need data, even if outside --start/--end.
    start = min(args.start, args.event_start - timedelta(days=21), args.focus_day)
    end = max(args.end, args.focus_day)
    raw_dir = args.data_dir / "raw"
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Fetching {start} to {end} from Elexon BMRS ({args.concurrency} concurrent requests)")
    raw = asyncio.run(fetch.fetch_all(start, end, raw_dir, concurrency=args.concurrency, transport=transport))
    try:
        bmunits = asyncio.run(fetch.fetch_bmu_reference(args.data_dir, transport=transport))
    except Exception as exc:  # fuel split is a nice-to-have; carry on without it
        print(f"  BM unit reference data unavailable ({exc}); fuel groups use unit names only")
        bmunits = None

    units = transform.unit_cashflows(raw, bmunits)
    in_range = units.filter(pl.col("settlementDate").is_between(args.start, args.end))
    daily = transform.daily(units)
    monthly = transform.monthly(in_range)
    by_fuel = transform.monthly_bid_payments_by_fuel(in_range)
    hh = transform.half_hourly(units, raw["system_prices"], args.focus_day)

    # Full-detail tables (every column, in £ and MWh); each chart also writes
    # its own CSV of just what it plots.
    full_dir = args.out_dir / "data" / "full"
    full_dir.mkdir(parents=True, exist_ok=True)
    daily.write_csv(full_dir / "daily_bid_offer.csv")
    monthly.write_csv(full_dir / "monthly_bid_offer.csv")
    by_fuel.write_csv(full_dir / "monthly_bid_payments_by_fuel.csv")
    hh.write_csv(full_dir / f"half_hourly_{args.focus_day.isoformat()}.csv")

    style.ensure_fonts(args.data_dir / "fonts")
    style.apply()
    ev_from = args.event_start.replace(day=1)
    ev_to = min(args.end, ev_from.replace(month=ev_from.month % 12 + 1, year=ev_from.year + ev_from.month // 12)
                - timedelta(days=1))
    outputs = [
        charts.monthly_costs(monthly, args.out_dir),
        charts.monthly_volumes(monthly, args.out_dir),
        charts.bid_payments_by_fuel(by_fuel, args.out_dir),
        charts.event_daily(daily, ev_from, ev_to, args.event_start, args.event_end, args.out_dir,
                           f"04_daily_{ev_from:%Y_%m}"),
        charts.focus_day(hh, args.focus_day, args.out_dir),
    ]
    today = date.today()
    workbook = report.write_workbook(outputs, args.out_dir / "bm_charts_data.xlsx", today)
    report.write_html(outputs, args.out_dir / "report.html", today, workbook)
    _summary(monthly, daily, args)
    return outputs


def _summary(monthly, daily, args) -> None:
    print("\nCalendar-year totals (£m paid out, TWh accepted):")
    by_year = (
        monthly.with_columns(pl.col("month").dt.year().alias("year"))
        .group_by("year")
        .agg(
            (pl.col("paid_out_offer").sum() / 1e6).round(0).alias("offers_£m"),
            (pl.col("paid_out_bid").sum() / 1e6).round(0).alias("bids_£m"),
            (pl.col("net_total").sum() / 1e6).round(0).alias("net_£m"),
            (pl.col("volume_mwh_bid").sum() / 1e6).round(2).alias("bid_TWh"),
            (pl.col("volume_mwh_offer").sum() / 1e6).round(2).alias("offer_TWh"),
        )
        .sort("year")
    )
    with pl.Config(tbl_rows=20):
        print(by_year)
    ev = daily.filter(pl.col("settlementDate").is_between(args.event_start, args.event_end))
    print(f"\nEvent {args.event_start} to {args.event_end}:")
    print(ev.select("settlementDate", (pl.col("paid_out_offer") / 1e6).round(2).alias("offers_£m"),
                    (pl.col("paid_out_bid") / 1e6).round(2).alias("bids_£m")))


def main(argv=None) -> None:
    args = parse_args(argv)
    for chart in run(args):
        print(f"wrote {chart.png} (data: {chart.csv})")
    print(f"wrote {args.out_dir / 'bm_charts_data.xlsx'}")
    print(f"wrote {args.out_dir / 'report.html'}")

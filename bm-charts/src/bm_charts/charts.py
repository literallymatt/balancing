"""Deck-ready charts. Each function writes one PNG (and an SVG twin)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import polars as pl
from matplotlib.ticker import FuncFormatter

from . import style

SOURCE = "Source: Elexon BMRS Insights API, indicative settlement cashflows and volumes"


def _figure(nrows: int = 1, height_ratios=None):
    fig, axes = plt.subplots(
        nrows, 1, figsize=style.FIGSIZE, sharex=True,
        gridspec_kw={"height_ratios": height_ratios} if height_ratios else None,
    )
    fig.subplots_adjust(left=0.07, right=0.985, top=0.86, bottom=0.18, hspace=0.25)
    return fig, axes


def _caption(fig, text: str) -> None:
    """Small unit caption top-left, like the deck's chart labels."""
    fig.text(0.07, 0.93, text, fontsize=18, color=style.MUTED, ha="left", va="center")


def _source(fig, text: str = SOURCE) -> None:
    fig.text(0.985, 0.01, text, fontsize=12, color=style.SUBTLE, ha="right", va="bottom")


def _legend(fig, handles_labels) -> None:
    handles, labels = handles_labels
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.985, 0.97), ncol=len(labels))


def _save(fig, out_dir: Path, name: str) -> Path:
    path = out_dir / f"{name}.png"
    fig.savefig(path, dpi=style.DPI)
    fig.savefig(out_dir / f"{name}.svg")
    plt.close(fig)
    return path


def _millions(ax) -> None:
    """£m tick labels, with a decimal when the scale is small."""
    decimals = 1 if ax.get_ylim()[1] < 10 else 0
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"£{v:,.{decimals}f}m"))


def _month_axis(ax) -> None:
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))


def monthly_costs(monthly: pl.DataFrame, out_dir: Path) -> Path:
    """Stacked monthly money paid out by NESO: offers below, bids on top."""
    m = monthly.sort("month")
    x = m["month"].to_list()
    offer = (m["paid_out_offer"] / 1e6).to_list()
    bid = (m["paid_out_bid"] / 1e6).to_list()
    fig, ax = _figure()
    width = 24  # days; leaves a visible gap between monthly bars
    ax.bar(x, offer, width=width, color=style.OFFER, label="Offers (pay to increase output or cut demand)",
           edgecolor=style.BACKGROUND, linewidth=1)
    ax.bar(x, bid, width=width, bottom=offer, color=style.BID, label="Bids (pay to turn down)",
           edgecolor=style.BACKGROUND, linewidth=1)
    _millions(ax)
    _month_axis(ax)
    _caption(fig, "Monthly Balancing Mechanism payments by NESO, £m")
    _legend(fig, ax.get_legend_handles_labels())
    _source(fig)
    return _save(fig, out_dir, "01_monthly_bid_offer_costs")


def monthly_volumes(monthly: pl.DataFrame, out_dir: Path) -> Path:
    """Mirrored monthly accepted volumes: offers up, bids down, in TWh."""
    m = monthly.sort("month")
    x = m["month"].to_list()
    offer = (m["volume_mwh_offer"] / 1e6).to_list()
    bid = (-m["volume_mwh_bid"] / 1e6).to_list()
    fig, ax = _figure()
    ax.bar(x, offer, width=24, color=style.OFFER, label="Offer volume accepted")
    ax.bar(x, bid, width=24, color=style.BID, label="Bid volume accepted")
    ax.axhline(0, color=style.INK, linewidth=1.2)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{abs(v):.1f} TWh"))
    _month_axis(ax)
    _caption(fig, "Accepted BM volume per month, TWh (bids below the line)")
    _legend(fig, ax.get_legend_handles_labels())
    _source(fig)
    return _save(fig, out_dir, "02_monthly_bid_offer_volumes")


def bid_payments_by_fuel(by_fuel: pl.DataFrame, out_dir: Path) -> Path:
    """Who gets paid to turn down: stacked monthly bid payments by fuel."""
    wide = (
        by_fuel.pivot(on="fuelGroup", index="month", values="paid_out")
        .fill_null(0.0)
        .sort("month")
    )
    groups = [g for g in style.FUEL_COLOURS if g in wide.columns and wide[g].sum() > 0]
    x = wide["month"].to_list()
    fig, ax = _figure()
    bottom = [0.0] * len(x)
    for g in groups:
        vals = (wide[g] / 1e6).to_list()
        ax.bar(x, vals, width=24, bottom=bottom, color=style.FUEL_COLOURS[g], label=g,
               edgecolor=style.BACKGROUND, linewidth=1)
        bottom = [b + v for b, v in zip(bottom, vals)]
    _millions(ax)
    _month_axis(ax)
    _caption(fig, "Monthly payments to turn down (bids), by technology, £m")
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", bbox_to_anchor=(0.985, 0.985), ncol=4, fontsize=14)
    fig.subplots_adjust(top=0.82)
    _source(fig)
    return _save(fig, out_dir, "03_bid_payments_by_fuel")


def event_daily(daily: pl.DataFrame, start: date, end: date, event_start: date, event_end: date,
                out_dir: Path, name: str, caption: str) -> Path:
    """Daily payments around an event, with the event days shaded."""
    d = daily.filter(pl.col("settlementDate").is_between(start, end)).sort("settlementDate")
    x = d["settlementDate"].to_list()
    offer = (d["paid_out_offer"] / 1e6).to_list()
    bid = (d["paid_out_bid"] / 1e6).to_list()
    fig, ax = _figure()
    ax.axvspan(mdates.date2num(event_start) - 0.5, mdates.date2num(event_end) + 0.5,
               color=style.EVENT_BAND, zorder=0)
    ax.text(mdates.date2num(event_start) - 0.4, 0.97, "Heatwave", transform=ax.get_xaxis_transform(),
            color=style.EVENT_EDGE, fontsize=16, fontweight=600, va="top")
    ax.bar(x, offer, width=0.75, color=style.OFFER, label="Offers")
    ax.bar(x, bid, width=0.75, bottom=offer, color=style.BID, label="Bids (paid to turn down)",
           edgecolor=style.BACKGROUND, linewidth=1)
    _millions(ax)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    # %-d is glibc-only; build the unpadded day by hand so it works on Windows too
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{mdates.num2date(v).day} {mdates.num2date(v):%b}"))
    _caption(fig, caption)
    _legend(fig, ax.get_legend_handles_labels())
    _source(fig)
    return _save(fig, out_dir, name)


def focus_day(hh: pl.DataFrame, day: date, out_dir: Path) -> Path:
    """Half-hourly payments on one day, with system buy price in its own panel."""
    sp = hh["settlementPeriod"].to_list()
    offer = (hh["paid_out_offer"] / 1e3).to_list()
    bid = (hh["paid_out_bid"] / 1e3).to_list()
    fig, (ax, ax2) = _figure(2, height_ratios=[2.2, 1])
    ax.bar(sp, offer, width=0.75, color=style.OFFER, label="Offers")
    ax.bar(sp, bid, width=0.75, bottom=offer, color=style.BID, label="Bids (paid to turn down)",
           edgecolor=style.BACKGROUND, linewidth=1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"£{v:,.0f}k"))
    ax2.plot(sp, hh["systemBuyPrice"].to_list(), color=style.HEADING, linewidth=2)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"£{v:,.0f}"))
    ax2.set_title("System buy price, £/MWh", loc="left", fontsize=15, color=style.MUTED)
    ticks = list(range(1, len(sp) + 1, 4))
    ax2.set_xticks(ticks, [f"{(t - 1) // 2:02d}:{'30' if (t - 1) % 2 else '00'}" for t in ticks])
    ax2.set_xlim(0.4, len(sp) + 0.6)
    _caption(fig, f"Balancing Mechanism payments per half hour, {day.day} {day:%B %Y}, £k")
    _legend(fig, ax.get_legend_handles_labels())
    _source(fig)
    return _save(fig, out_dir, f"05_focus_day_{day.isoformat()}")

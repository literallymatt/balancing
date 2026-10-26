"""Deck-ready charts. Each function writes one chart (PNG and SVG) plus a CSV of
exactly the numbers it plots, and returns a ``Chart`` describing both."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import polars as pl
from matplotlib.ticker import FuncFormatter

from . import style

SOURCE = "Source: Elexon BMRS Insights API, indicative settlement cashflows and volumes"

# Figure-fraction layout shared by every chart, so titles, legends and plot
# edges line up when the charts sit next to each other in a deck.
LEFT_TEXT = 0.012
LEFT, RIGHT = 0.07, 0.985
TITLE_Y, SUBTITLE_Y, LEGEND_Y = 0.955, 0.875, 0.81
PLOT_TOP, PLOT_BOTTOM = 0.735, 0.2
RULE_Y, SOURCE_Y = 0.065, 0.03


@dataclass
class Chart:
    name: str
    sheet: str  # Excel sheet name, at most 31 characters
    title: str
    subtitle: str
    png: Path
    svg: Path
    csv: Path
    data: pl.DataFrame


def _span(months: list[date]) -> str:
    return f"{min(months):%b %Y} to {max(months):%b %Y}"


def _figure(nrows: int = 1, height_ratios=None, bottom: float = PLOT_BOTTOM):
    fig, axes = plt.subplots(
        nrows, 1, figsize=style.FIGSIZE, sharex=True,
        gridspec_kw={"height_ratios": height_ratios} if height_ratios else None,
    )
    fig.subplots_adjust(left=LEFT, right=RIGHT, top=PLOT_TOP, bottom=bottom, hspace=0.32)
    return fig, axes


def _frame(fig, title: str, subtitle: str, handles_labels, name: str, legend_size: float = 15) -> None:
    """Title, subtitle, legend row and source footer, in the same place on every chart."""
    fig.text(LEFT_TEXT, TITLE_Y, title, fontsize=26, color=style.HEADING, ha="left", va="top",
             **style.heading_font())
    fig.text(LEFT_TEXT, SUBTITLE_Y, subtitle, fontsize=17, color=style.MUTED, ha="left", va="top")
    handles, labels = handles_labels
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(LEFT_TEXT, LEGEND_Y), ncol=len(labels),
               fontsize=legend_size, borderpad=0, borderaxespad=0, handlelength=0.9, handleheight=0.9,
               handletextpad=0.5, columnspacing=1.8)
    fig.add_artist(plt.Line2D([LEFT_TEXT, RIGHT], [RULE_Y, RULE_Y], transform=fig.transFigure,
                              color=style.GRID, linewidth=1.2))
    fig.text(LEFT_TEXT, SOURCE_Y, SOURCE, fontsize=12, color=style.SUBTLE, ha="left", va="center")
    fig.text(RIGHT, SOURCE_Y, f"Data: data/{name}.csv", fontsize=12, color=style.SUBTLE, ha="right",
             va="center")


def _save(fig, out_dir: Path, name: str, sheet: str, title: str, subtitle: str, data: pl.DataFrame) -> Chart:
    chart_dir, data_dir = out_dir / "charts", out_dir / "data"
    chart_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    png, svg, csv = chart_dir / f"{name}.png", chart_dir / f"{name}.svg", data_dir / f"{name}.csv"
    fig.savefig(png, dpi=style.DPI)
    fig.savefig(svg)
    plt.close(fig)
    data.write_csv(csv, include_bom=True)  # BOM so Excel reads the £ signs as UTF-8
    return Chart(name, sheet, title, subtitle, png, svg, csv, data)


def _millions(ax) -> None:
    """£m tick labels, with a decimal when the scale is small."""
    decimals = 1 if ax.get_ylim()[1] < 10 else 0
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"£{v:,.{decimals}f}m"))


def _month_axis(ax) -> None:
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.margins(x=0.01)


def monthly_costs(monthly: pl.DataFrame, out_dir: Path) -> Chart:
    """Stacked monthly money paid out by NESO: offers below, bids on top."""
    data = monthly.sort("month").select(
        pl.col("month").alias("Month"),
        (pl.col("paid_out_offer") / 1e6).round(3).alias("Offers paid out (£m)"),
        (pl.col("paid_out_bid") / 1e6).round(3).alias("Bids paid out (£m)"),
        ((pl.col("paid_out_offer") + pl.col("paid_out_bid")) / 1e6).round(3).alias("Total paid out (£m)"),
    )
    x = data["Month"].to_list()
    offer, bid = data["Offers paid out (£m)"].to_list(), data["Bids paid out (£m)"].to_list()
    fig, ax = _figure()
    width = 24  # days; leaves a visible gap between monthly bars
    ax.bar(x, offer, width=width, color=style.OFFER, label="Offers (pay to increase output or cut demand)",
           edgecolor=style.BACKGROUND, linewidth=1)
    ax.bar(x, bid, width=width, bottom=offer, color=style.BID, label="Bids (pay to turn down)",
           edgecolor=style.BACKGROUND, linewidth=1)
    _millions(ax)
    _month_axis(ax)
    name = "01_monthly_bid_offer_costs"
    title = "Balancing Mechanism payments by month"
    subtitle = f"Money paid out by NESO for accepted offers and bids, £m, {_span(x)}"
    _frame(fig, title, subtitle, ax.get_legend_handles_labels(), name)
    return _save(fig, out_dir, name, "01 Monthly payments", title, subtitle, data)


def monthly_volumes(monthly: pl.DataFrame, out_dir: Path) -> Chart:
    """Mirrored monthly accepted volumes: offers up, bids down, in TWh."""
    data = monthly.sort("month").select(
        pl.col("month").alias("Month"),
        (pl.col("volume_mwh_offer") / 1e6).round(4).alias("Offer volume accepted (TWh)"),
        (pl.col("volume_mwh_bid") / 1e6).round(4).alias("Bid volume accepted (TWh)"),
    )
    x = data["Month"].to_list()
    fig, ax = _figure()
    ax.bar(x, data["Offer volume accepted (TWh)"].to_list(), width=24, color=style.OFFER,
           label="Offer volume accepted")
    ax.bar(x, (-data["Bid volume accepted (TWh)"]).to_list(), width=24, color=style.BID,
           label="Bid volume accepted")
    ax.axhline(0, color=style.INK, linewidth=1.2)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{abs(v):.1f} TWh"))
    _month_axis(ax)
    name = "02_monthly_bid_offer_volumes"
    title = "Accepted Balancing Mechanism volume by month"
    subtitle = f"Offer volume above the line, bid volume below, TWh, {_span(x)}"
    _frame(fig, title, subtitle, ax.get_legend_handles_labels(), name)
    return _save(fig, out_dir, name, "02 Monthly volumes", title, subtitle, data)


def bid_payments_by_fuel(by_fuel: pl.DataFrame, out_dir: Path) -> Chart:
    """Who gets paid to turn down: stacked monthly bid payments by fuel."""
    wide = (
        by_fuel.pivot(on="fuelGroup", index="month", values="paid_out")
        .fill_null(0.0)
        .sort("month")
    )
    groups = [g for g in style.FUEL_COLOURS if g in wide.columns and wide[g].sum() > 0]
    data = wide.select(
        pl.col("month").alias("Month"),
        *[(pl.col(g) / 1e6).round(3).alias(f"{g} (£m)") for g in groups],
        (pl.sum_horizontal(groups) / 1e6).round(3).alias("Total (£m)"),
    )
    x = data["Month"].to_list()
    fig, ax = _figure()
    bottom = [0.0] * len(x)
    for g in groups:
        vals = data[f"{g} (£m)"].to_list()
        ax.bar(x, vals, width=24, bottom=bottom, color=style.FUEL_COLOURS[g], label=g,
               edgecolor=style.BACKGROUND, linewidth=1)
        bottom = [b + v for b, v in zip(bottom, vals)]
    _millions(ax)
    _month_axis(ax)
    name = "03_bid_payments_by_fuel"
    title = "Payments to turn down, by technology"
    subtitle = f"Bid payments paid out by NESO each month, £m, {_span(x)}"
    _frame(fig, title, subtitle, ax.get_legend_handles_labels(), name, legend_size=14)
    return _save(fig, out_dir, name, "03 Bid payments by fuel", title, subtitle, data)


def event_daily(daily: pl.DataFrame, start: date, end: date, event_start: date, event_end: date,
                out_dir: Path, name: str, event_label: str = "Heatwave") -> Chart:
    """Daily payments around an event, with the event days shaded."""
    data = daily.filter(pl.col("settlementDate").is_between(start, end)).sort("settlementDate").select(
        pl.col("settlementDate").alias("Date"),
        (pl.col("paid_out_offer") / 1e6).round(3).alias("Offers paid out (£m)"),
        (pl.col("paid_out_bid") / 1e6).round(3).alias("Bids paid out (£m)"),
        pl.col("settlementDate").is_between(event_start, event_end).alias(event_label),
    )
    x = data["Date"].to_list()
    offer = data["Offers paid out (£m)"].to_list()
    fig, ax = _figure(bottom=0.15)  # one-line tick labels need less room
    ax.axvspan(mdates.date2num(event_start) - 0.5, mdates.date2num(event_end) + 0.5,
               color=style.EVENT_BAND, zorder=0)
    ax.text(mdates.date2num(event_start) - 0.35, 0.98, event_label, transform=ax.get_xaxis_transform(),
            color=style.EVENT_EDGE, fontsize=16, fontweight=600, va="top")
    ax.bar(x, offer, width=0.75, color=style.OFFER, label="Offers")
    ax.bar(x, data["Bids paid out (£m)"].to_list(), width=0.75, bottom=offer, color=style.BID,
           label="Bids (paid to turn down)", edgecolor=style.BACKGROUND, linewidth=1)
    _millions(ax)
    ax.set_xlim(mdates.date2num(start) - 0.6, mdates.date2num(end) + 0.6)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=2))
    # %-d is glibc-only; build the unpadded day by hand so it works on Windows too
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{mdates.num2date(v).day} {mdates.num2date(v):%b}"))
    title = f"Daily Balancing Mechanism payments, {start:%B %Y}"
    subtitle = (f"Offers and bids paid out by NESO, £m. Shaded: {event_label.lower()}, "
                f"{event_start.day} {event_start:%b} to {event_end.day} {event_end:%b}")
    _frame(fig, title, subtitle, ax.get_legend_handles_labels(), name)
    return _save(fig, out_dir, name, f"04 Daily {start:%b %Y}", title, subtitle, data)


def focus_day(hh: pl.DataFrame, day: date, out_dir: Path) -> Chart:
    """Half-hourly payments on one day, with system buy price in its own panel."""
    data = hh.sort("settlementPeriod").select(
        pl.col("settlementPeriod").alias("Settlement period"),
        pl.col("settlementPeriod").map_elements(
            lambda sp: f"{(sp - 1) // 2:02d}:{'30' if (sp - 1) % 2 else '00'}", return_dtype=pl.Utf8
        ).alias("Start time"),
        (pl.col("paid_out_offer") / 1e3).round(2).alias("Offers paid out (£k)"),
        (pl.col("paid_out_bid") / 1e3).round(2).alias("Bids paid out (£k)"),
        pl.col("systemBuyPrice").round(2).alias("System buy price (£/MWh)"),
    )
    sp = data["Settlement period"].to_list()
    offer = data["Offers paid out (£k)"].to_list()
    fig, (ax, ax2) = _figure(2, height_ratios=[2.2, 1], bottom=0.12)
    ax.bar(sp, offer, width=0.75, color=style.OFFER, label="Offers")
    ax.bar(sp, data["Bids paid out (£k)"].to_list(), width=0.75, bottom=offer, color=style.BID,
           label="Bids (paid to turn down)", edgecolor=style.BACKGROUND, linewidth=1)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"£{v:,.0f}k"))
    ax2.plot(sp, data["System buy price (£/MWh)"].to_list(), color=style.HEADING, linewidth=2)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"£{v:,.0f}"))
    ax2.set_title("System buy price, £/MWh", loc="left", fontsize=15, color=style.MUTED)
    ticks = list(range(1, len(sp) + 1, 4))
    ax2.set_xticks(ticks, [data["Start time"][t - 1] for t in ticks])
    ax2.set_xlim(0.4, len(sp) + 0.6)
    name = f"05_focus_day_{day.isoformat()}"
    title = f"Balancing Mechanism payments per half hour, {day.day} {day:%B %Y}"
    subtitle = "Offers and bids paid out by NESO, £k, with the system buy price below"
    _frame(fig, title, subtitle, ax.get_legend_handles_labels(), name)
    return _save(fig, out_dir, name, f"05 Half-hourly {day.isoformat()}", title, subtitle, data)

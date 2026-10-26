"""Deck-ready charts in the Newsprint style. Each function writes one chart
(PNG and SVG) plus a CSV of exactly the numbers it plots, and returns a
``Chart`` describing both.

Headlines state the chart's main finding and are worked out from the data on
every run; the subtitle says what is plotted, in what unit, over what range.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import polars as pl
from matplotlib.ticker import FuncFormatter, MaxNLocator

from . import style

SOURCE = "Source: Elexon BMRS Insights API, indicative settlement cashflows and volumes"

# One description of each side, used in every legend, so bids and offers
# always read the same way whichever chart they appear in.
OFFERS = "Offers (increase output or reduce demand)"
BIDS = "Bids (reduce output or increase demand)"

# Figure-fraction layout shared by every chart, so headlines, legends and plot
# edges line up when the charts sit next to each other in a deck. Values sit
# on the right-hand axis, beyond RIGHT.
LEFT_TEXT, LEFT, RIGHT = 0.012, 0.016, 0.93
PLOT_BOTTOM, SOURCE_Y = 0.13, 0.03
TITLE_SIZE, SUBTITLE_SIZE = 28, 16.5


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


def _day(d: date, year: bool = False) -> str:
    # %-d is glibc-only; build the unpadded day by hand so it works on Windows too
    return f"{d.day} {d:%B %Y}" if year else f"{d.day} {d:%b}"


def _money_m(v: float) -> str:
    """£ millions as a headline figure: £508m, £2.3bn, £9.5m."""
    if v >= 1000:
        return f"£{v / 1000:.1f}bn"
    return f"£{v:.1f}m" if v < 10 else f"£{v:,.0f}m"


def _figure(nrows: int = 1, height_ratios=None):
    fig, axes = plt.subplots(
        nrows, 1, figsize=style.FIGSIZE, sharex=True,
        gridspec_kw={"height_ratios": height_ratios} if height_ratios else None,
    )
    for ax in fig.axes:
        ax.yaxis.tick_right()
    return fig, axes


def _wrap(fig, text: str, width_in: float, **kw) -> list[str]:
    """Split text into lines no wider than width_in, measured in the real font."""
    renderer = fig.canvas.get_renderer()
    lines, line = [], []
    probe = fig.text(0, 0, "", **kw)
    for word in text.split():
        probe.set_text(" ".join(line + [word]))
        if line and probe.get_window_extent(renderer).width / fig.dpi > width_in:
            lines.append(" ".join(line))
            line = [word]
        else:
            line.append(word)
    probe.remove()
    return lines + [" ".join(line)]


def _frame(fig, title: str, subtitle: str, handles_labels, name: str, hspace: float = 0.2) -> None:
    """Headline, subtitle, legend row and footer, then fit the plot beneath them."""
    height, width = fig.get_figheight(), fig.get_figwidth()
    head = {"fontsize": TITLE_SIZE, "color": style.HEADING, **style.heading_font()}
    y = 0.22  # inches from the top edge
    for line in _wrap(fig, title, width * (RIGHT + 0.05 - LEFT_TEXT), **head):
        y += 0.46
        fig.text(LEFT_TEXT, 1 - y / height, line, va="baseline", **head)
    y += 0.36
    fig.text(LEFT_TEXT, 1 - y / height, subtitle, fontsize=SUBTITLE_SIZE, color=style.MUTED, va="baseline")
    handles, labels = handles_labels
    if handles:
        y += 0.2
        fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(LEFT_TEXT, 1 - y / height),
                   ncol=len(labels), borderpad=0, borderaxespad=0, handlelength=0.9, handleheight=0.9,
                   handletextpad=0.5, columnspacing=1.8)
        y += 0.3
    y += 0.42  # room for the unit label above the value axis
    fig.subplots_adjust(left=LEFT, right=RIGHT, top=1 - y / height, bottom=PLOT_BOTTOM, hspace=hspace)
    fig.text(LEFT_TEXT, SOURCE_Y, SOURCE, fontsize=11.5, color=style.SUBTLE, ha="left", va="center")
    fig.text(RIGHT + 0.05, SOURCE_Y, f"Data: data/{name}.csv", fontsize=11.5, color=style.SUBTLE,
             ha="right", va="center")


def _value_axis(ax, lo: float, hi: float, unit: str, fmt=None, nbins: int = 5) -> None:
    """Right-hand value axis on round numbers, with its unit printed above it."""
    ticks = MaxNLocator(nbins=nbins, steps=[1, 2, 2.5, 5, 10]).tick_values(lo, hi)
    ticks = [t for t in ticks if t >= lo - 1e-9 or t == ticks[0]]
    ax.set_ylim(ticks[0], ticks[-1])
    ax.set_yticks(ticks)
    step = ticks[1] - ticks[0]
    decimals = 0 if step >= 1 else 1 if step >= 0.1 else 2
    label = fmt or (lambda v, _: f"{v:,.{decimals}f}")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, pos: "0" if abs(v) < 1e-9 else label(v, pos)))
    pad = mtransforms.offset_copy(ax.transAxes, fig=ax.figure, x=10, y=12, units="points")
    ax.text(1, 1, unit, transform=pad, ha="left", va="bottom", fontsize=15, fontweight=600, color=style.MUTED)
    ax.axhline(0, color=style.INK, linewidth=1.4, zorder=3)


def _year_axis(ax, months: list[date]) -> None:
    """Year names centred under their months, with a tick between years."""
    nums = mdates.date2num(months)
    years = sorted({m.year for m in months})
    centres = [nums[[m.year == y for m in months]].mean() for y in years]
    ax.set_xticks([mdates.date2num(date(y, 1, 1)) - 15.5 for y in years[1:]])
    ax.set_xticklabels([])
    ax.tick_params(axis="x", which="major", length=10, width=1.2, color=style.SUBTLE)
    ax.set_xticks(centres, minor=True)
    ax.set_xticklabels([str(y) for y in years], minor=True)
    ax.tick_params(axis="x", which="minor", length=0, pad=10)
    ax.set_xlim(nums[0] - 20, nums[-1] + 20)


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


def _stack(ax, x, layers, width) -> None:
    """Stacked bars, each layer a (values, colour, label) triple, bottom first."""
    bottom = [0.0] * len(x)
    for vals, colour, label in layers:
        ax.bar(x, vals, width=width, bottom=bottom, color=colour, label=label,
               edgecolor=style.BACKGROUND, linewidth=0.8)
        bottom = [b + v for b, v in zip(bottom, vals)]


def monthly_costs(monthly: pl.DataFrame, out_dir: Path) -> Chart:
    """Stacked monthly money paid out by NESO: offers below, bids on top."""
    data = monthly.sort("month").select(
        pl.col("month").alias("Month"),
        (pl.col("paid_out_offer") / 1e6).round(3).alias("Offers paid out (£m)"),
        (pl.col("paid_out_bid") / 1e6).round(3).alias("Bids paid out (£m)"),
        ((pl.col("paid_out_offer") + pl.col("paid_out_bid")) / 1e6).round(3).alias("Total paid out (£m)"),
    )
    x = data["Month"].to_list()
    total = data["Total paid out (£m)"]
    fig, ax = _figure()
    _stack(ax, x, [(data["Offers paid out (£m)"].to_list(), style.OFFER, OFFERS),
                   (data["Bids paid out (£m)"].to_list(), style.BID, BIDS)], width=24)
    _value_axis(ax, 0, total.max(), "£m")
    _year_axis(ax, x)
    peak = total.arg_max()
    title = (f"Balancing Mechanism payments reached {_money_m(total[peak])} in {x[peak]:%B %Y}, "
             f"the highest month since {x[0]:%B %Y}")
    subtitle = f"Money paid out by NESO for accepted offers and bids each month, £m, {_span(x)}"
    name = "01_monthly_bid_offer_costs"
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
    offer, bid = data["Offer volume accepted (TWh)"], data["Bid volume accepted (TWh)"]
    fig, ax = _figure()
    ax.bar(x, offer.to_list(), width=24, color=style.OFFER, label=OFFERS)
    ax.bar(x, (-bid).to_list(), width=24, color=style.BID, label=BIDS)
    _value_axis(ax, -bid.max(), offer.max(), "TWh", fmt=lambda v, _: f"{abs(v):.1f}")
    _year_axis(ax, x)
    avg_offer, avg_bid = offer.mean(), bid.mean()
    closeness = "close to" if 0.8 <= avg_bid / avg_offer <= 1.25 else "against"
    title = f"NESO accepts {avg_bid:.1f} TWh of bids a month on average, {closeness} {avg_offer:.1f} TWh of offers"
    subtitle = f"Accepted Balancing Mechanism volume each month, offers above the line and bids below, TWh, {_span(x)}"
    name = "02_monthly_bid_offer_volumes"
    _frame(fig, title, subtitle, ax.get_legend_handles_labels(), name)
    return _save(fig, out_dir, name, "02 Monthly volumes", title, subtitle, data)


def bid_payments_by_fuel(by_fuel: pl.DataFrame, out_dir: Path) -> Chart:
    """Who gets paid to reduce output: stacked monthly bid payments by fuel."""
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
    _stack(ax, x, [(data[f"{g} (£m)"].to_list(), style.FUEL_COLOURS[g], g) for g in groups], width=24)
    _value_axis(ax, 0, data["Total (£m)"].max(), "£m")
    _year_axis(ax, x)
    total = data["Total (£m)"].sum()
    wind = data["Wind (£m)"].sum() if "Wind" in groups else 0.0
    title = (f"Wind farms received {wind / total:.0%} of the {_money_m(total)} paid to reduce output "
             f"since {x[0]:%B %Y}")
    subtitle = f"Bid payments made by NESO each month, by technology, £m, {_span(x)}"
    name = "03_bid_payments_by_fuel"
    _frame(fig, title, subtitle, ax.get_legend_handles_labels(), name)
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
    total = data["Offers paid out (£m)"] + data["Bids paid out (£m)"]
    fig, ax = _figure()
    ax.axvspan(mdates.date2num(event_start) - 0.5, mdates.date2num(event_end) + 0.5,
               color=style.EVENT_BAND, zorder=0, linewidth=0)
    ax.text(mdates.date2num(event_start) - 0.35, 0.97, event_label, transform=ax.get_xaxis_transform(),
            color=style.EVENT_EDGE, fontsize=14.5, fontweight=600, va="top")
    _stack(ax, x, [(data["Offers paid out (£m)"].to_list(), style.OFFER, OFFERS),
                   (data["Bids paid out (£m)"].to_list(), style.BID, BIDS)], width=0.75)
    _value_axis(ax, 0, total.max(), "£m")
    ticks = [d for d in x if d.day % 7 == 1]
    ax.set_xticks(mdates.date2num(ticks), [_day(d) for d in ticks])
    ax.tick_params(axis="x", length=6, width=1.2, color=style.SUBTLE)
    ax.set_xlim(mdates.date2num(start) - 0.6, mdates.date2num(end) + 0.6)

    peak = total.arg_max()
    p = x[peak]
    label = event_label.lower()
    if event_start <= p <= event_end:
        when = f"during the {label}"
    elif p > event_end:
        n = (p - event_end).days
        when = f"{n} day{'s' if n > 1 else ''} after the {label} ended"
    else:
        n = (event_start - p).days
        when = f"{n} day{'s' if n > 1 else ''} before the {label}"
    title = f"Daily payments peaked at {_money_m(total[peak])} on {_day(p)}, {when}"
    subtitle = (f"Money paid out by NESO for accepted offers and bids each day, £m, {start:%B %Y}. "
                f"Shaded: {label}, {_day(event_start)} to {_day(event_end)}")
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
    times = data["Start time"].to_list()
    total = data["Offers paid out (£k)"] + data["Bids paid out (£k)"]
    price = data["System buy price (£/MWh)"].fill_null(0.0)
    fig, (ax, ax2) = _figure(2, height_ratios=[1.7, 1])
    _stack(ax, sp, [(data["Offers paid out (£k)"].to_list(), style.OFFER, OFFERS),
                    (data["Bids paid out (£k)"].to_list(), style.BID, BIDS)], width=0.75)
    _value_axis(ax, 0, total.max(), "£k", nbins=4)

    ax2.plot(sp, price.to_list(), color=style.INK, linewidth=2)
    _value_axis(ax2, min(0.0, price.min()), price.max(), "£/MWh", nbins=3)
    ax2.set_title("System buy price", loc="left", fontsize=14.5, fontweight=600, color=style.MUTED, pad=12)
    top = price.arg_max()
    ax2.plot([sp[top]], [price[top]], "o", color=style.INK, markersize=7, markeredgecolor=style.BACKGROUND)
    ax2.annotate(f"£{price[top]:,.0f}/MWh at {times[top]}", (sp[top], price[top]), xytext=(0, 9),
                 textcoords="offset points", ha="center" if sp[top] < len(sp) - 4 else "right",
                 va="bottom", fontsize=14, fontweight=600, color=style.INK)
    ticks = sp[::6]
    ax2.set_xticks(ticks, [times[t - 1] for t in ticks])
    ax2.tick_params(axis="x", length=6, width=1.2, color=style.SUBTLE)
    ax2.set_xlim(0.4, len(sp) + 0.6)

    peak = total.arg_max()
    amount = f"£{total[peak] / 1000:.1f}m" if total[peak] >= 1000 else f"£{total[peak]:,.0f}k"
    title = f"Payments peaked at {amount} at {times[peak]}, when the system buy price was £{price[peak]:,.0f}/MWh"
    subtitle = (f"Money paid out by NESO for accepted offers and bids each half hour, £k, "
                f"{_day(day, year=True)}, with the system buy price below")
    name = f"05_focus_day_{day.isoformat()}"
    _frame(fig, title, subtitle, ax.get_legend_handles_labels(), name, hspace=0.55)
    return _save(fig, out_dir, name, f"05 Half-hourly {day.isoformat()}", title, subtitle, data)

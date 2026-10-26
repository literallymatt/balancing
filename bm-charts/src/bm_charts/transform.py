"""Polars transforms from raw BMRS frames to chart-ready tables.

Sign conventions follow Elexon settlement. A BM unit's cashflow is accepted
volume times price, positive when NESO pays the unit:

* Offers (increase generation or reduce demand): volume > 0, cashflow
  is normally positive, so it is a cost to the system.
* Bids (reduce generation or increase demand): volume < 0. A gas plant
  with a positive bid price pays NESO back (negative cashflow); a wind farm
  with a negative bid price is paid to turn down (positive cashflow).

So for both sides, the positive part of the cashflow is money paid out by
NESO, and the sum of everything is the net BM cost.
"""

from __future__ import annotations

import polars as pl

# Grouping used for the "who is paid" charts. Anything unlisted (nuclear,
# biomass, coal, oil) falls into "Other" to keep the chart to seven colours.
FUEL_GROUPS = {
    "WIND": "Wind",
    "CCGT": "Gas",
    "OCGT": "Gas",
    "GAS": "Gas",
    "PS": "Hydro and pumped storage",
    "NPSHYD": "Hydro and pumped storage",
    "BATTERY": "Batteries",
    "BESS": "Batteries",
}


def fuel_group_expr() -> pl.Expr:
    """Map a unit to a readable group, using its fuel type then its name."""
    fuel = pl.col("fuelType").fill_null("").str.to_uppercase()
    unit = pl.col("bmUnit").fill_null("")
    mapped = fuel.replace_strict(FUEL_GROUPS, default=None)
    return (
        pl.when(mapped.is_not_null())
        .then(mapped)
        .when(fuel.str.starts_with("INT") | unit.str.starts_with("I_"))
        .then(pl.lit("Interconnectors"))
        .when(unit.str.starts_with("V__") | unit.str.starts_with("2__") | (pl.col("bmUnitType") == "V"))
        .then(pl.lit("Supplier and VLP units (incl. DSR)"))
        .when(unit.str.contains("(?i)BESS|BATT"))
        .then(pl.lit("Batteries"))
        .otherwise(pl.lit("Other"))
        .alias("fuelGroup")
    )


# The volume endpoint gives each unit and period four rows, one per stage of
# the system price calculation. "Tagged" holds the total accepted volume: its
# daily sum matches the system-wide totalAccepted{Offer,Bid}Volume published
# with system prices, which the other three stages do not.
ACCEPTED_VOLUME_TYPE = "Tagged"

KEY = ["settlementDate", "settlementPeriod", "bmUnit"]


def _check_unique(df: pl.DataFrame, name: str) -> None:
    """Refuse to join on a key that repeats, which would multiply cashflows."""
    dupes = df.height - df.select(KEY).n_unique()
    if dupes:
        raise ValueError(f"{name} has {dupes} repeated unit/period rows; totals would be overcounted")


def unit_cashflows(raw: dict[str, pl.DataFrame], bmunits: pl.DataFrame | None) -> pl.DataFrame:
    """One row per unit, period and side, with paid-out and paid-back split."""
    frames = []
    for side in ("bid", "offer"):
        # The feed occasionally repeats a row verbatim (e.g. 2023-03-25); drop
        # exact copies, but let any conflicting repeats fail the check below.
        cash = raw[f"cashflow_{side}"].unique(maintain_order=True)
        vol = raw[f"volume_{side}"].filter(pl.col("dataType") == ACCEPTED_VOLUME_TYPE).select(
            *KEY, "totalVolumeAccepted"
        ).unique(maintain_order=True)
        _check_unique(cash, f"cashflow_{side}")
        _check_unique(vol, f"volume_{side}")
        frames.append(
            cash.join(vol, on=KEY, how="left")
            .with_columns(pl.lit(side).alias("side"))
        )
    df = pl.concat(frames, how="diagonal_relaxed")
    if bmunits is not None and bmunits.height:
        df = df.join(bmunits.select("bmUnit", "fuelType").unique("bmUnit"), on="bmUnit", how="left")
    else:
        df = df.with_columns(pl.lit(None, pl.Utf8).alias("fuelType"))
    return df.with_columns(
        fuel_group_expr(),
        pl.col("totalCashflow").clip(lower_bound=0).alias("paidOut"),
        pl.col("totalCashflow").clip(upper_bound=0).alias("paidBack"),
        pl.col("totalVolumeAccepted").abs().alias("volumeAbs"),
    )


def _side_totals(df: pl.DataFrame, by: list[str]) -> pl.DataFrame:
    """Wide table of costs (GBP) and volumes (MWh) per bid/offer side."""
    agg = df.group_by([*by, "side"]).agg(
        pl.col("totalCashflow").sum().alias("net"),
        pl.col("paidOut").sum().alias("paid_out"),
        pl.col("paidBack").sum().alias("paid_back"),
        pl.col("volumeAbs").sum().alias("volume_mwh"),
    )
    wide = agg.pivot(on="side", index=by, values=["net", "paid_out", "paid_back", "volume_mwh"])
    values = [f"{m}_{s}" for m in ("net", "paid_out", "paid_back", "volume_mwh") for s in ("bid", "offer")]
    for col in values:
        if col not in wide.columns:
            wide = wide.with_columns(pl.lit(0.0).alias(col))
    return wide.with_columns(pl.col(values).fill_null(0.0)).with_columns(
        (pl.col("net_bid") + pl.col("net_offer")).alias("net_total"),
    ).sort(by)


def daily(df: pl.DataFrame) -> pl.DataFrame:
    return _side_totals(df, ["settlementDate"])


def monthly(df: pl.DataFrame) -> pl.DataFrame:
    out = _side_totals(
        df.with_columns(pl.col("settlementDate").dt.truncate("1mo").alias("month")), ["month"]
    )
    return out.with_columns(
        (pl.col("net_offer") / pl.col("volume_mwh_offer")).alias("avg_offer_price"),
        (pl.col("paid_out_bid") / pl.col("volume_mwh_bid")).alias("avg_bid_payment"),
    )


def monthly_bid_payments_by_fuel(df: pl.DataFrame) -> pl.DataFrame:
    """Money paid out to units for bids (turning down), by fuel group and month."""
    return (
        df.filter(pl.col("side") == "bid")
        .with_columns(pl.col("settlementDate").dt.truncate("1mo").alias("month"))
        .group_by("month", "fuelGroup")
        .agg(pl.col("paidOut").sum().alias("paid_out"), pl.col("volumeAbs").sum().alias("volume_mwh"))
        .sort("month", "fuelGroup")
    )


def half_hourly(df: pl.DataFrame, prices: pl.DataFrame, day) -> pl.DataFrame:
    """Per settlement period costs for one day, with system prices attached."""
    hh = _side_totals(df.filter(pl.col("settlementDate") == day), ["settlementDate", "settlementPeriod"])
    p = prices.filter(pl.col("settlementDate") == day).select(
        "settlementPeriod", "systemBuyPrice", "systemSellPrice", "netImbalanceVolume"
    )
    n_periods = max(48, p.get_column("settlementPeriod").max() or 48)
    periods = pl.DataFrame({"settlementPeriod": range(1, n_periods + 1)}, schema={"settlementPeriod": pl.Int32})
    cost_cols = [c for c in hh.columns if c not in ("settlementDate", "settlementPeriod")]
    return (
        periods.join(hh.drop("settlementDate"), on="settlementPeriod", how="left")
        .with_columns(pl.col(cost_cols).fill_null(0.0))
        .join(p, on="settlementPeriod", how="left")
    )

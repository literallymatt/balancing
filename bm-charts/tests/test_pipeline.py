"""Offline end-to-end test: a mock transport stands in for the BMRS API."""

import random
import re
import zipfile
from datetime import date

import httpx
import polars as pl

from bm_charts import cli, transform

UNITS = [("T_WIND-1", "T", "WIND"), ("T_CCGT-1", "T", "CCGT"), ("V__DSR-1", "V", None)]
STAGES = {"Original": 0.7, "Original-Priced": 0.2, "Re-priced": 0.05, "Tagged": 1.0}


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    rng = random.Random(path)
    if path.endswith("/reference/bmunits/all"):
        return httpx.Response(200, json=[
            {"elexonBmUnit": u, "nationalGridBmUnit": u[2:], "fuelType": f} for u, _, f in UNITS
        ])
    day = path.rsplit("/", 1)[-1]
    if "/system-prices/" in path:
        return httpx.Response(200, json={"data": [
            {"settlementDate": day, "settlementPeriod": sp, "startTime": f"{day}T00:00:00Z",
             "systemSellPrice": 80.0, "systemBuyPrice": 80.0 + sp, "netImbalanceVolume": 0.0,
             "totalAcceptedOfferVolume": 100.0, "totalAcceptedBidVolume": -200.0}
            for sp in range(1, 49)
        ]})
    side = "bid" if "/bid/" in path else "offer"
    rows = []
    for sp in range(1, 49):
        for unit, utype, fuel in UNITS:
            vol = rng.uniform(10, 100) * (-1 if side == "bid" else 1)
            price = (-70 if fuel == "WIND" else 40) if side == "bid" else 120
            rec = {"settlementDate": day, "settlementPeriod": sp, "bmUnit": unit, "bmUnitType": utype}
            if "/cashflows/" in path:
                rows.append(rec | {"totalCashflow": vol * price, "bidOfferPairCashflows": {"negative1": vol * price}})
            else:
                # Like the real DISPTAV feed: one row per price-calculation stage,
                # and only "Tagged" carries the full accepted volume.
                for data_type, share in STAGES.items():
                    rows.append(rec | {"dataType": data_type, "totalVolumeAccepted": vol * share,
                                       "pairVolumes": {"negative1": vol * share}})
    return httpx.Response(200, json={"data": rows})


def test_end_to_end(tmp_path):
    args = cli.parse_args([
        "--start", "2026-05-25", "--end", "2026-07-03",
        "--data-dir", str(tmp_path / "data"), "--out-dir", str(tmp_path / "out"),
    ])
    outputs = cli.run(args, transport=httpx.MockTransport(handler))
    assert len(outputs) == 5
    assert all(c.png.exists() and c.svg.exists() and c.csv.exists() for c in outputs)
    assert (tmp_path / "out" / "bm_charts_data.xlsx").exists()
    assert (tmp_path / "out" / "report.html").exists()

    # Each chart's CSV holds what it plots: monthly costs in £m, totals adding up.
    costs = pl.read_csv(outputs[0].csv)
    assert costs.height == 3
    assert (costs["Offers paid out (£m)"] + costs["Bids paid out (£m)"]
            - costs["Total paid out (£m)"]).abs().max() < 0.01
    with zipfile.ZipFile(tmp_path / "out" / "bm_charts_data.xlsx") as z:
        sheets = re.findall(r'<sheet name="([^"]+)"', z.read("xl/workbook.xml").decode())
    assert sheets == ["About"] + [c.sheet for c in outputs]

    full = tmp_path / "out" / "data" / "full"
    monthly = pl.read_csv(full / "monthly_bid_offer.csv")
    assert monthly.height == 3
    # Totals equal the raw API figures: the four volume rows per unit must not
    # multiply cashflows, and volume is the "Tagged" stage only.
    raw = tmp_path / "data" / "raw"
    for side in ("bid", "offer"):
        cash = pl.read_parquet(raw / f"cashflow_{side}" / "*.parquet").filter(
            pl.col("settlementDate").is_between(args.start, args.end))
        vol = pl.read_parquet(raw / f"volume_{side}" / "*.parquet").filter(
            pl.col("settlementDate").is_between(args.start, args.end) & (pl.col("dataType") == "Tagged"))
        assert abs(monthly[f"paid_out_{side}"].sum() - cash["totalCashflow"].clip(lower_bound=0).sum()) < 1e-6 * monthly[f"paid_out_{side}"].sum()
        assert abs(monthly[f"volume_mwh_{side}"].sum() - vol["totalVolumeAccepted"].abs().sum()) < 1e-6 * monthly[f"volume_mwh_{side}"].sum()
    # Wind is paid to turn down, gas pays back, so bid paid_out comes from wind only.
    fuel = pl.read_csv(full / "monthly_bid_payments_by_fuel.csv")
    paid = fuel.group_by("fuelGroup").agg(pl.col("paid_out").sum())
    assert paid.filter(pl.col("fuelGroup") == "Gas")["paid_out"][0] == 0
    assert paid.filter(pl.col("fuelGroup") == "Wind")["paid_out"][0] > 0
    assert "Supplier and VLP units (incl. DSR)" in fuel["fuelGroup"].to_list()


def test_cache_is_reused(tmp_path):
    calls = []

    def counting(request):
        calls.append(request.url.path)
        return handler(request)

    args = cli.parse_args([
        "--start", "2026-06-01", "--end", "2026-06-02", "--event-start", "2026-06-22",
        "--focus-day", "2026-06-02",
        "--data-dir", str(tmp_path / "data"), "--out-dir", str(tmp_path / "out"),
    ])
    cli.run(args, transport=httpx.MockTransport(counting))
    first = len(calls)
    cli.run(args, transport=httpx.MockTransport(counting))
    assert len(calls) == first  # second run reads every day from cache


def test_fuel_group_fallbacks():
    df = pl.DataFrame({
        "bmUnit": ["I_IEG-IFA2", "V__ABC001", "E_BESS-1", "T_X"],
        "bmUnitType": ["I", "V", "E", "T"],
        "fuelType": [None, None, None, "NUCLEAR"],
    })
    groups = df.select(transform.fuel_group_expr())["fuelGroup"].to_list()
    assert groups == ["Interconnectors", "Supplier and VLP units (incl. DSR)", "Batteries", "Other"]

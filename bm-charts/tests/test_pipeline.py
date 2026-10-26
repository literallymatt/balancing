"""Offline end-to-end test: a mock transport stands in for the BMRS API."""

import random
from datetime import date

import httpx
import polars as pl

from bm_charts import cli, transform

UNITS = [("T_WIND-1", "T", "WIND"), ("T_CCGT-1", "T", "CCGT"), ("V__DSR-1", "V", None)]


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
                rec |= {"totalCashflow": vol * price, "bidOfferPairCashflows": {"negative1": vol * price}}
            else:
                rec |= {"totalVolumeAccepted": vol, "pairVolumes": {"negative1": vol}}
            rows.append(rec)
    return httpx.Response(200, json={"data": rows})


def test_end_to_end(tmp_path):
    args = cli.parse_args([
        "--start", "2026-05-25", "--end", "2026-07-03",
        "--data-dir", str(tmp_path / "data"), "--out-dir", str(tmp_path / "out"),
    ])
    outputs = cli.run(args, transport=httpx.MockTransport(handler))
    assert len(outputs) == 5 and all(p.exists() for p in outputs)

    monthly = pl.read_csv(tmp_path / "out" / "monthly_bid_offer.csv")
    assert monthly.height == 3
    # Wind is paid to turn down, gas pays back, so bid paid_out comes from wind only.
    fuel = pl.read_csv(tmp_path / "out" / "monthly_bid_payments_by_fuel.csv")
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

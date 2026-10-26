"""Async fetching from the Elexon BMRS Insights API.

Every dataset here is requested one settlement date at a time. Each day is
cached as a parquet file under ``data/raw/<dataset>/<date>.parquet`` so a
rerun only fetches days it does not already have.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import httpx
import polars as pl

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

# Elexon publishes no hard rate limit, but it is a shared public service.
# Eight requests in flight is quick enough (a few years of data in minutes)
# without hammering it. Retries back off on 429 and 5xx.
DEFAULT_CONCURRENCY = 8
MAX_RETRIES = 5

# Indicative settlement data is revised for a few days after the event, so
# the most recent days are always refetched rather than read from cache.
REFRESH_DAYS = 5


@dataclass(frozen=True)
class Dataset:
    name: str
    path: str  # formatted with {date}

    def url(self, day: date) -> str:
        return self.path.format(date=day.isoformat())


DATASETS = {
    "cashflow_bid": Dataset(
        "cashflow_bid", "/balancing/settlement/indicative/cashflows/all/bid/{date}"
    ),
    "cashflow_offer": Dataset(
        "cashflow_offer", "/balancing/settlement/indicative/cashflows/all/offer/{date}"
    ),
    "volume_bid": Dataset(
        "volume_bid", "/balancing/settlement/indicative/volumes/all/bid/{date}"
    ),
    "volume_offer": Dataset(
        "volume_offer", "/balancing/settlement/indicative/volumes/all/offer/{date}"
    ),
    "system_prices": Dataset(
        "system_prices", "/balancing/settlement/system-prices/{date}"
    ),
}

# Only the columns the analysis needs; nested bid-offer pair detail is dropped.
KEEP_COLUMNS = {
    "cashflow_bid": ["settlementDate", "settlementPeriod", "bmUnit", "bmUnitType", "leadPartyName", "totalCashflow"],
    "cashflow_offer": ["settlementDate", "settlementPeriod", "bmUnit", "bmUnitType", "leadPartyName", "totalCashflow"],
    "volume_bid": ["settlementDate", "settlementPeriod", "bmUnit", "bmUnitType", "totalVolumeAccepted"],
    "volume_offer": ["settlementDate", "settlementPeriod", "bmUnit", "bmUnitType", "totalVolumeAccepted"],
    "system_prices": [
        "settlementDate", "settlementPeriod", "startTime", "systemSellPrice", "systemBuyPrice",
        "netImbalanceVolume", "totalAcceptedOfferVolume", "totalAcceptedBidVolume",
    ],
}


def date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def records_to_frame(dataset: str, records: list[dict]) -> pl.DataFrame:
    """Flatten an API ``data`` array into a typed frame with the kept columns."""
    cols = KEEP_COLUMNS[dataset]
    rows = [{c: r.get(c) for c in cols} for r in records]
    frame = pl.DataFrame(rows, schema={c: _dtype(c) for c in cols}, strict=False)
    return frame.with_columns(pl.col("settlementDate").str.to_date())


def _dtype(col: str) -> pl.DataType:
    if col == "settlementPeriod":
        return pl.Int32
    if col in {"settlementDate", "startTime", "bmUnit", "bmUnitType", "leadPartyName"}:
        return pl.Utf8
    return pl.Float64


async def _get_json(client: httpx.AsyncClient, url: str, sem: asyncio.Semaphore) -> dict:
    for attempt in range(MAX_RETRIES):
        async with sem:
            try:
                resp = await client.get(url, params={"format": "json"})
            except httpx.TransportError:
                resp = None
        if resp is not None and resp.status_code == 200:
            return resp.json()
        if resp is not None and resp.status_code == 404:
            return {"data": []}
        if resp is not None and resp.status_code not in (429, 500, 502, 503, 504):
            resp.raise_for_status()
        retry_after = resp.headers.get("Retry-After") if resp is not None else None
        wait = float(retry_after) if retry_after else 2**attempt + random.random()
        await asyncio.sleep(wait)
    raise RuntimeError(f"Gave up on {url} after {MAX_RETRIES} attempts")


async def _fetch_day(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    dataset: str,
    day: date,
    cache_dir: Path,
) -> pl.DataFrame:
    path = cache_dir / dataset / f"{day.isoformat()}.parquet"
    fresh = day >= date.today() - timedelta(days=REFRESH_DAYS)
    if path.exists() and not fresh:
        return pl.read_parquet(path)
    payload = await _get_json(client, DATASETS[dataset].url(day), sem)
    frame = records_to_frame(dataset, payload.get("data") or [])
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(path)
    return frame


async def fetch_all(
    start: date,
    end: date,
    cache_dir: Path,
    datasets: list[str] | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, pl.DataFrame]:
    """Fetch every (dataset, day) pair concurrently and concatenate per dataset."""
    datasets = datasets or list(DATASETS)
    days = date_range(start, end)
    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=60, limits=limits, transport=transport
    ) as client:
        jobs = [(ds, d) for ds in datasets for d in days]
        total = len(jobs)
        done = 0

        async def run(ds: str, d: date) -> tuple[str, pl.DataFrame]:
            nonlocal done
            frame = await _fetch_day(client, sem, ds, d, cache_dir)
            done += 1
            if done % 500 == 0 or done == total:
                print(f"  fetched {done}/{total} day-files", flush=True)
            return ds, frame

        results = await asyncio.gather(*(run(ds, d) for ds, d in jobs))

    out: dict[str, list[pl.DataFrame]] = {ds: [] for ds in datasets}
    for ds, frame in results:
        if frame.height:
            out[ds].append(frame)
    return {
        ds: pl.concat(frames) if frames else records_to_frame(ds, [])
        for ds, frames in out.items()
    }


async def fetch_bmu_reference(cache_dir: Path, transport: httpx.AsyncBaseTransport | None = None) -> pl.DataFrame:
    """BM unit reference data, used to map units to fuel type."""
    path = cache_dir / "bmunits.parquet"
    if path.exists():
        return pl.read_parquet(path)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60, transport=transport) as client:
        resp = await client.get("/reference/bmunits/all")
        resp.raise_for_status()
        payload = resp.json()
    records = payload["data"] if isinstance(payload, dict) else payload
    rows = [
        {
            "bmUnit": r.get("elexonBmUnit"),
            "nationalGridBmUnit": r.get("nationalGridBmUnit"),
            "fuelType": r.get("fuelType"),
        }
        for r in records
    ]
    frame = pl.DataFrame(rows, schema={"bmUnit": pl.Utf8, "nationalGridBmUnit": pl.Utf8, "fuelType": pl.Utf8})
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(path)
    return frame

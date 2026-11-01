"""Async fetching from the Elexon BMRS Insights API.

Every dataset here is requested one settlement date at a time: Elexon offers
no date-range or bulk version of the indicative cashflow (EBOCF), volume
(DISPTAV) or system price (DISEBSP) endpoints. Each day is cached as a parquet
file under ``data/raw/<dataset>/<date>.parquet`` so a rerun only fetches days
it does not already have.

The day files are large (a day of volumes is tens of MB of JSON), and decoding
them takes longer than downloading them. So the event loop only downloads, and
a process pool decodes and writes each day on the other CPU cores. Otherwise
the decoding runs one day at a time and the downloads sit waiting for it.
"""

from __future__ import annotations

import asyncio
import json
import multiprocessing
import os
import random
import time
from concurrent.futures import Executor, ProcessPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import httpx
import polars as pl

from .transform import ACCEPTED_VOLUME_TYPE

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
    # The volume endpoint (DISPTAV) returns each unit four times, one row per
    # system-price calculation stage in ``dataType``; transform picks one.
    "volume_bid": ["settlementDate", "settlementPeriod", "bmUnit", "bmUnitType", "dataType", "totalVolumeAccepted"],
    "volume_offer": ["settlementDate", "settlementPeriod", "bmUnit", "bmUnitType", "dataType", "totalVolumeAccepted"],
    "system_prices": [
        "settlementDate", "settlementPeriod", "startTime", "systemSellPrice", "systemBuyPrice",
        "netImbalanceVolume", "totalAcceptedOfferVolume", "totalAcceptedBidVolume",
    ],
}


# Rows the analysis never uses are dropped before caching. The volume feed
# repeats every unit four times, once per price-calculation stage, and only
# one stage is used, so this cuts the volume cache to a quarter.
ROW_FILTERS = {
    "volume_bid": ("dataType", ACCEPTED_VOLUME_TYPE),
    "volume_offer": ("dataType", ACCEPTED_VOLUME_TYPE),
}


def date_range(start: date, end: date) -> list[date]:
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def records_to_frame(dataset: str, records: list[dict]) -> pl.DataFrame:
    """Flatten an API ``data`` array into a typed frame with the kept columns."""
    cols = KEEP_COLUMNS[dataset]
    if dataset in ROW_FILTERS:
        key, value = ROW_FILTERS[dataset]
        records = [r for r in records if r.get(key) == value]
    data = {c: [r.get(c) for r in records] for c in cols}
    frame = pl.DataFrame(data, schema={c: _dtype(c) for c in cols}, strict=False)
    return frame.with_columns(pl.col("settlementDate").str.to_date())


def decode_and_cache(dataset: str, content: bytes, path: str) -> None:
    """Decode one day's JSON response and write it to the cache.

    Runs in a worker process, so it takes and returns only plain values.
    """
    payload = json.loads(content) if content else {}
    frame = records_to_frame(dataset, payload.get("data") or [])
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(path)


def _dtype(col: str) -> pl.DataType:
    if col == "settlementPeriod":
        return pl.Int32
    if col in {"settlementDate", "startTime", "bmUnit", "bmUnitType", "leadPartyName", "dataType"}:
        return pl.Utf8
    return pl.Float64


async def _get_bytes(client: httpx.AsyncClient, url: str, sem: asyncio.Semaphore) -> bytes:
    """GET a URL and return the raw body, b"" for a day with no data."""
    for attempt in range(MAX_RETRIES):
        async with sem:
            try:
                resp = await client.get(url, params={"format": "json"})
            except httpx.TransportError:
                resp = None
        if resp is not None and resp.status_code == 200:
            return resp.content
        if resp is not None and resp.status_code == 404:
            return b""
        if resp is not None and resp.status_code not in (429, 500, 502, 503, 504):
            resp.raise_for_status()
        retry_after = resp.headers.get("Retry-After") if resp is not None else None
        wait = float(retry_after) if retry_after else 2**attempt + random.random()
        await asyncio.sleep(wait)
    raise RuntimeError(f"Gave up on {url} after {MAX_RETRIES} attempts")


def _cache_path(cache_dir: Path, dataset: str, day: date) -> Path:
    return cache_dir / dataset / f"{day.isoformat()}.parquet"


def _is_cached(path: Path, dataset: str, day: date) -> bool:
    if day >= date.today() - timedelta(days=REFRESH_DAYS) or not path.exists():
        return False
    # Files cached before a column was added to KEEP_COLUMNS are refetched.
    # Only the parquet footer is read here, not the data.
    return set(KEEP_COLUMNS[dataset]) <= set(pl.read_parquet_schema(path))


def _load_cached(cache_dir: Path, dataset: str, days: list[date]) -> pl.DataFrame:
    cols = KEEP_COLUMNS[dataset]
    frames = [
        pl.read_parquet(_cache_path(cache_dir, dataset, d), columns=cols)
        for d in days
    ]
    frames = [f for f in frames if f.height]
    if not frames:
        return records_to_frame(dataset, [])
    out = pl.concat(frames, how="vertical_relaxed")
    if dataset in ROW_FILTERS:
        # Day files cached before ROW_FILTERS existed still hold every row.
        key, value = ROW_FILTERS[dataset]
        out = out.filter(pl.col(key) == value)
    return out


async def fetch_all(
    start: date,
    end: date,
    cache_dir: Path,
    datasets: list[str] | None = None,
    concurrency: int = DEFAULT_CONCURRENCY,
    transport: httpx.AsyncBaseTransport | None = None,
    executor: Executor | None = None,
) -> dict[str, pl.DataFrame]:
    """Fetch every missing (dataset, day) pair, then load each dataset from cache.

    Downloads run ``concurrency`` at a time on the event loop. Decoding runs in
    ``executor``, a process pool sized to the machine's cores by default.
    """
    datasets = datasets or list(DATASETS)
    days = date_range(start, end)
    jobs = [
        (ds, d) for ds in datasets for d in days
        if not _is_cached(_cache_path(cache_dir, ds, d), ds, d)
    ]
    total = len(jobs)
    print(f"  {len(datasets) * len(days) - total} day-files cached, {total} to fetch", flush=True)

    if jobs:
        own_executor = executor is None
        if own_executor:
            # "spawn", not Linux's default "fork": forking a process that
            # already runs Polars' thread pool can deadlock the workers.
            # macOS and Windows use spawn anyway.
            executor = ProcessPoolExecutor(
                max_workers=max(1, min(os.cpu_count() or 1, concurrency)),
                mp_context=multiprocessing.get_context("spawn"),
            )
        try:
            await _download(jobs, cache_dir, concurrency, transport, executor)
        finally:
            if own_executor:
                executor.shutdown()

    return {ds: _load_cached(cache_dir, ds, days) for ds in datasets}


async def _download(
    jobs: list[tuple[str, date]],
    cache_dir: Path,
    concurrency: int,
    transport: httpx.AsyncBaseTransport | None,
    executor: Executor,
) -> None:
    loop = asyncio.get_running_loop()
    sem = asyncio.Semaphore(concurrency)
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    total = len(jobs)
    done = 0
    nbytes = 0
    started = time.monotonic()

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=60, limits=limits, transport=transport
    ) as client:

        async def run(ds: str, d: date) -> None:
            nonlocal done, nbytes
            content = await _get_bytes(client, DATASETS[ds].url(d), sem)
            path = _cache_path(cache_dir, ds, d)
            await loop.run_in_executor(executor, decode_and_cache, ds, content, str(path))
            done += 1
            nbytes += len(content)
            if done % 250 == 0 or done == total:
                elapsed = time.monotonic() - started
                print(
                    f"  fetched {done}/{total} day-files, {nbytes / 1e6:,.0f} MB of JSON in "
                    f"{elapsed:,.0f}s ({done / elapsed:.1f} files/s)",
                    flush=True,
                )

        await asyncio.gather(*(run(ds, d) for ds, d in jobs))


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

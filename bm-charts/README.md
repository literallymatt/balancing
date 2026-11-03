# bm-charts

Pulls Balancing Mechanism bid and offer data from the public Elexon BMRS
Insights API (no API key needed) and draws deck-ready charts.

The charts use a "Newsprint" style: tinted paper, a serif headline stating
each chart's main finding (worked out from the data on every run, so check it
reads right before it goes in a deck), values and units on the right-hand
axis, and the same description of bids and offers in every legend.

## Run it

```bash
uv sync
uv run bm-charts
```

The first full run fetches every day from 1 Jan 2023 to yesterday: five
datasets a day, about 7,000 requests, eight at a time. Elexon has no bulk or
date-range version of these endpoints, so one request per dataset per day is
the floor. Each day is cached in `data/raw/`, so later runs only fetch new days
(plus the last five days, which Elexon revises).

The day files are big, and decoding the JSON used to take longer than
downloading it. Decoding now runs in a pool of worker processes, one per CPU
core, while the main loop keeps downloading. Progress lines show files per
second, so if a run looks network-bound (CPU mostly idle), try
`--concurrency 16` and drop back if you see 429 errors. Only the "Tagged" rows
of the volume feed are cached, which makes `data/raw/` much smaller.

For a quick first look, try a shorter range:

```bash
uv run bm-charts --start 2026-01-01
```

Useful options:

| Option | Default | What it does |
|---|---|---|
| `--start`, `--end` | 2023-01-01, yesterday | Range for the monthly charts |
| `--event-start`, `--event-end` | 2026-06-22, 2026-06-26 | Days shaded on the daily chart (the heatwave) |
| `--focus-day` | 2026-06-23 | Day for the half-hourly chart |
| `--concurrency` | 8 | Requests in flight at once. Drop it if you see 429 errors |

## What you get in `output/`

| Path | What it is |
|---|---|
| `report.html` | Every chart on one page, with links to its data. Charts are embedded, so the file can be sent on its own |
| `bm_charts_data.xlsx` | The data behind every chart, one sheet each, plus an About sheet with definitions |
| `charts/` | Each chart as a PNG (for slides) and an SVG |
| `data/` | One CSV per chart, holding exactly the numbers it plots, in the chart's units |
| `data/full/` | Full-detail tables in £ and MWh, including the `paid_back_*` and `net_*` columns |

The charts:

| Chart | Shows |
|---|---|
| `01_monthly_bid_offer_costs` | Money NESO paid out each month, offers and bids stacked |
| `02_monthly_bid_offer_volumes` | Accepted offer volume above the line, bid volume below |
| `03_bid_payments_by_fuel` | Who is paid to turn down, by technology (wind shows the constraint story) |
| `04_daily_2026_06` | Daily payments through June 2026 with the heatwave shaded |
| `05_focus_day_2026-06-23` | Half-hourly payments on the focus day, with the system price below |

The console prints calendar-year totals and the heatwave days.

## Data and definitions

Endpoints (all per settlement date):

- `/balancing/settlement/indicative/cashflows/all/{bid|offer}/{date}`
- `/balancing/settlement/indicative/volumes/all/{bid|offer}/{date}`
- `/balancing/settlement/system-prices/{date}`
- `/reference/bmunits/all` for each unit's fuel type

A unit's cashflow is accepted volume times price, positive when NESO pays the
unit. Offers are almost always paid. Bids go both ways: a gas plant with a
positive bid price pays NESO back to turn down, while a wind farm with a
negative bid price is paid to turn down. The charts show **money paid out**
(the positive cashflows) on each side. The CSVs in `data/full/` also hold
`paid_back_*` and `net_*` columns.

These are **Balancing Mechanism** costs from Elexon's indicative settlement
data. They are a large part of, but not the same as, NESO's total balancing
costs (which also include trades outside the BM, reserve and ancillary
services contracts). Expect the totals to sit below the £bn figures on the
annual costs slide.

## NESO annual costs on the MBSS basis

```bash
uv run neso-mbss
```

This pulls NESO's Monthly Balancing Services Summary, the series behind its
headline annual costs, from the links on its public balancing costs page. It
writes `output/data/07_neso_mbss_annual_calendar_year.csv`, plus monthly and
financial-year CSVs in `output/data/full/`.

- **Constraints** is NESO's whole Constraints category: thermal, voltage, ROCOF
  and intertrips. **Thermal** is the workbooks' `BM - Transmission` and
  `Trades - Transmission` lines. The CSVs NESO has used since April 2025 don't
  split it out, so thermal is empty from then on.
- **April 2017 to March 2019** isn't in the MBSS files on that page. Those months
  are rebuilt from daily BSUoS costs plus MBSS daily ancillary services, which
  lands within about 2% of MBSS where the two overlap. See `rebuilt_months`.
- **The daily BSUoS data alone runs lower** because it leaves out ancillary
  services, so `neso-costs` won't match NESO's headline figures.

## Tests

```bash
uv run pytest
```

The tests run the whole pipeline offline against a mock API.

# bm-charts

Pulls Balancing Mechanism bid and offer data from the public Elexon BMRS
Insights API (no API key needed) and draws charts in the style of the
*Margins, Constraints and the Case for Flexibility* deck.

## Run it

```bash
uv sync
uv run bm-charts
```

The first full run fetches every day from 1 Jan 2023 to yesterday: five
datasets a day, about 7,000 requests, eight at a time. Expect roughly 10 to 20
minutes. Each day is cached in `data/raw/`, so later runs only fetch new days
(plus the last five days, which Elexon revises).

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

## Tests

```bash
uv run pytest
```

The tests run the whole pipeline offline against a mock API.

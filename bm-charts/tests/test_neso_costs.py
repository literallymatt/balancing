"""Offline test: a mock NESO portal with two financial-year files."""

from datetime import date, timedelta

import httpx
import polars as pl

from bm_charts import neso_costs


def _csv(start: date, days: int) -> str:
    rows = ["SETT_DATE,SETT_PERIOD,Energy Imbalance,Constraints,Total"]
    for i in range(days):
        d = start + timedelta(days=i)
        for sp in (1, 2):
            rows.append(f"{d:%d/%m/%Y},{sp},100,400,500")
    return "\n".join(rows)


FILES = {"fy2324.csv": _csv(date(2023, 4, 1), 366), "fy2425.csv": _csv(date(2024, 4, 1), 365)}


def handler(request: httpx.Request) -> httpx.Response:
    if request.url.path.endswith("/package_show"):
        return httpx.Response(200, json={"result": {"resources": [
            {"name": "Daily Balancing Costs 2024-2025", "format": "CSV", "url": "https://x.test/fy2425.csv"},
            {"name": "Missing Settlement Periods", "format": "XLSX", "url": "https://x.test/m.xlsx"},
            {"name": "Daily Balancing Costs 2023-2024", "format": "CSV", "url": "https://x.test/fy2324.csv"},
        ]}})
    return httpx.Response(200, text=FILES[request.url.path.lstrip("/")])


def test_calendar_and_financial_years(tmp_path):
    daily = neso_costs.to_daily(neso_costs.fetch(tmp_path, transport=httpx.MockTransport(handler)))
    assert daily.height == 731 and daily["total"][0] == 1000  # two periods a day summed
    cy = neso_costs.by_year(daily)
    assert cy["year"].to_list() == ["2023", "2024", "2025"]
    y2024 = cy.filter(pl.col("year") == "2024")
    assert y2024["days"][0] == 366 and y2024["total_£m"][0] == round(366 * 1000 / 1e6, 1)
    assert y2024["Constraints_£m"][0] == round(366 * 800 / 1e6, 1)
    fy = neso_costs.by_year(daily, financial=True)
    assert fy["year"].to_list() == ["2023/24", "2024/25"]
    assert fy["days"].to_list() == [366, 365]

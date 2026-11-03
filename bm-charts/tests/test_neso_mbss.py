"""Offline tests: MBSS workbooks, CSVs and the early-year rebuild, built in memory."""

import io
import zipfile
from datetime import date, datetime, timedelta

import openpyxl
import polars as pl
import pytest

from bm_charts import neso_mbss

MONTHS = [datetime(2024 + (m < 4), m, 1) for m in (*range(4, 13), 1, 2, 3)]


def _workbook() -> bytes:
    wb = openpyxl.Workbook()
    wb.active.title = "Total categories"
    sheet = wb["Total categories"]
    sheet.append([None, "Cost £m", *MONTHS])
    for category in neso_mbss.CATEGORIES:
        sheet.append([None, category, *([100.0 if category == "Constraints" else 1.0] * 12)])
    sheet.append([None, "Total", *([110.0] * 12)])
    sheet.append([None, "Volume MWh", *MONTHS])
    sheet.append([None, "Constraints", *([9999.0] * 12)])
    constraints = wb.create_sheet("Constraints")
    constraints.append([None, "Costs (£m)"])
    constraints.append([None, "BM - Transmission", *([70.0] * 12)])
    constraints.append([None, "Trades - Transmission", *([10.0] * 12)])
    constraints.append([None, "BM - Voltage", *([20.0] * 12)])
    constraints.append([None, "Absolute Volume MWh"])
    constraints.append([None, "BM - Transmission", *([5000.0] * 12)])
    constraints.append([None, "Trades - Transmission", *([5000.0] * 12)])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def _zip(files: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)
    return out.getvalue()


CSV_HEADER = ("﻿Restoration*,Reactive*,Constraints - England & Wales,Constraints - Cheviot^,Constraints - Scotland,"
              "Constraints - Ancillary Services*,ROCOF,Constrained Sterilised HR,Response,Year,Month\n")


def _total_csv(*months: tuple[int, str]) -> bytes:
    rows = "".join(f"1000000,2000000,3000000,4000000,5000000,6000000,7000000,8000000,9000000,{y},{m}\n" for y, m in months)
    return (CSV_HEADER + rows).encode()


def test_workbook_uses_cost_tables_not_volume_tables():
    df = neso_mbss.parse_workbook(_workbook())
    assert df.height == 12 and df["month"][0] == date(2024, 4, 1)
    assert df["Constraints"][0] == 100 and df["total"][0] == 110
    assert df["thermal_constraints"][0] == 80  # transmission only, not voltage or volumes


def test_csv_maps_columns_onto_workbook_categories():
    df = neso_mbss.parse_total_csv(_total_csv((2025, "April")))
    row = df.row(0, named=True)
    assert row["month"] == date(2025, 4, 1)
    assert row["Constraints"] == 3 + 4 + 5 + 6 + 7 + 8
    assert row["Black Start"] == 1 and row["Reactive"] == 2 and row["Response"] == 9
    assert row["thermal_constraints"] is None and row["total"] == 45


def test_csv_rejects_unknown_columns():
    with pytest.raises(ValueError, match="Mystery"):
        neso_mbss.parse_total_csv(b"Mystery,Year,Month\n1,2025,April\n")


def test_lists_only_mbss_documents():
    page = """
    <a href="/document/1/download">Monthly Balancing Services Summary (MBSS) 2024/2025</a>
    <a href="https://www.neso.energy/document/2/download">Total Balancing Costs - Monthly Balancing Services Summary (MBSS) Data</a>
    <a href="/document/3/download">Daily balancing costs - May 2025</a>
    """
    years, rolling = neso_mbss.list_documents(page)
    assert years == {2024: "https://www.neso.energy/document/1/download"}
    assert rolling == {"Total Balancing Costs": "https://www.neso.energy/document/2/download"}


def test_monthly_stitches_sources_and_cuts_both_year_types():
    days = [date(2024, 3, 1) + timedelta(days=i) for i in range(31)]
    daily = pl.DataFrame({"date": days, "Constraints": [1e6] * 31, "total": [2e6] * 31})
    ancillary = ("﻿Year,Quarter,Month,Day,Fast Reserve,Constraints - Ancillary Services\n"
                 + "".join(f"2024,Qtr 1,March,{d},1000000,500000\n" for d in range(1, 32))
                 + "2024,Qtr 2,April,1,7000000,7000000\n").encode()
    years = {2024: _zip({"2024-25/MBSS Data March 2025.xlsx": _workbook(), "2024-25/MBSS Data May 2024.xlsx": b"ignored"})}
    rolling = {
        # March 2025 overrides the workbook, April 2025 extends it.
        "Total Balancing Costs": _total_csv((2025, "March"), (2025, "April")),
        "Ancillary Services Costs": ancillary,
    }
    monthly = neso_mbss.to_monthly(years, rolling, daily)
    assert monthly.height == 14

    rebuilt = monthly.filter(pl.col("month") == date(2024, 3, 1)).row(0, named=True)
    assert rebuilt["source"] == neso_mbss.REBUILT
    assert rebuilt["total"] == 31 * (2 + 1 + 0.5) and rebuilt["Constraints"] == 31 * 1.5
    assert monthly.filter(pl.col("month") == date(2025, 3, 1))["total"][0] == 45

    fy = neso_mbss.by_year(monthly, financial=True)
    assert fy["year"].to_list() == ["2023/24", "2024/25", "2025/26"]
    y2425 = fy.filter(pl.col("year") == "2024/25").row(0, named=True)
    assert y2425["months"] == 12 and y2425["total_£m"] == 11 * 110 + 45
    assert y2425["other_£m"] == y2425["total_£m"] - y2425["constraints_£m"]
    assert y2425["thermal_constraints_£m"] is None  # March came from a CSV, which has no thermal split
    cy = neso_mbss.by_year(monthly)
    assert cy["year"].to_list() == ["2024", "2025"]
    assert cy.filter(pl.col("year") == "2024").row(0, named=True)["rebuilt_months"] == 1

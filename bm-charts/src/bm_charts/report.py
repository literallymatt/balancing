"""Bundles the charts for sharing: an Excel workbook with one sheet of data per
chart, and an HTML page that lays the charts out with their titles and links."""

from __future__ import annotations

import base64
import html
from datetime import date
from pathlib import Path

import xlsxwriter

from . import style
from .charts import SOURCE, Chart

DEFINITIONS = [
    "Offers are paid when NESO asks a unit to increase output or cut demand.",
    "Bids are paid when NESO asks a unit to turn down. Some bids pay NESO back instead (e.g. gas "
    "plant saving fuel); the charts show only money paid out.",
    "These are Balancing Mechanism costs from Elexon's indicative settlement data, not NESO's total "
    "balancing costs, which also include trades outside the BM and ancillary services.",
]


def write_workbook(charts: list[Chart], path: Path, generated: date) -> Path:
    """One sheet per chart, preceded by an About sheet listing them."""
    wb = xlsxwriter.Workbook(path)
    title = wb.add_format({"bold": True, "font_size": 16, "font_color": style.HEADING})
    bold = wb.add_format({"bold": True})
    wrap = wb.add_format({"text_wrap": True, "valign": "top"})
    header = {"bold": True, "font_color": "#FFFFFF", "bg_color": style.HEADING, "text_wrap": True,
              "valign": "top"}

    about = wb.add_worksheet("About")
    about.set_column(0, 0, 28)
    about.set_column(1, 1, 100)
    about.write(0, 0, "Balancing Mechanism bid and offer costs", title)
    about.write(1, 0, f"Generated {generated:%d %B %Y}. {SOURCE}.")
    about.write(3, 0, "Sheet", bold)
    about.write(3, 1, "Chart", bold)
    for i, c in enumerate(charts, start=4):
        about.write_url(i, 0, f"internal:'{c.sheet}'!A1", string=c.sheet)
        about.write(i, 1, f"{c.title}. {c.subtitle}")
    row = len(charts) + 5
    about.write(row, 0, "Definitions", bold)
    for i, text in enumerate(DEFINITIONS, start=row + 1):
        about.write(i, 1, text, wrap)

    for c in charts:
        c.data.write_excel(workbook=wb, worksheet=c.sheet, header_format=header, autofit=True,
                           dtype_formats={date: "yyyy-mm-dd"}, float_precision=3,
                           include_header=True, freeze_panes=(1, 0))
    wb.close()
    return path


def write_html(charts: list[Chart], path: Path, generated: date, workbook: Path) -> Path:
    """Charts are embedded, so the page still shows them when sent on its own;
    the data and download links are relative to the output folder."""
    rel = lambda p: p.relative_to(path.parent).as_posix()  # noqa: E731
    embed = lambda p: "data:image/svg+xml;base64," + base64.b64encode(p.read_bytes()).decode()  # noqa: E731
    sections = "\n".join(
        # The chart image carries its own title and subtitle, so the page doesn't repeat them.
        f"""<section>
  <img src="{embed(c.svg)}" alt="{html.escape(f'{c.title}. {c.subtitle}')}">
  <p class="links"><a href="{rel(c.csv)}">Data (CSV)</a> · <a href="{rel(c.png)}">PNG</a> ·
  <a href="{rel(c.svg)}">SVG</a></p>
</section>"""
        for c in charts
    )
    definitions = "".join(f"<li>{html.escape(d)}</li>" for d in DEFINITIONS)
    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Balancing Mechanism costs</title>
<link rel="stylesheet" href="{style.FONT_CSS}&display=swap">
<style>
  body {{ margin: 0; background: {style.BACKGROUND}; color: {style.INK};
         font: 16px/1.5 "IBM Plex Sans", Arial, sans-serif; }}
  main {{ max-width: 1200px; margin: 0 auto; padding: 40px 16px 64px; }}
  h1 {{ font-family: "Space Grotesk", "IBM Plex Sans", sans-serif; color: {style.HEADING};
        font-weight: 600; font-size: 34px; margin: 0; }}
  .meta, .links, footer {{ color: {style.MUTED}; }}
  .meta {{ margin: 6px 0 0; }}
  section {{ border-top: 1px solid {style.GRID}; margin-top: 32px; padding-top: 24px; }}
  img {{ display: block; width: 100%; height: auto; }}
  a {{ color: {style.OFFER}; }}
  .links {{ font-size: 14px; margin: 10px 0 0; }}
  footer {{ border-top: 1px solid {style.GRID}; margin-top: 48px; padding-top: 20px; font-size: 14px; }}
  footer ul {{ padding-left: 20px; }}
</style>
</head>
<body>
<main>
  <h1>Balancing Mechanism bid and offer costs</h1>
  <p class="meta">Generated {generated.day} {generated:%B %Y} ·
  <a href="{rel(workbook)}">All chart data (Excel)</a></p>
{sections}
  <footer>
    <p>{html.escape(SOURCE)}.</p>
    <ul>{definitions}</ul>
  </footer>
</main>
</body>
</html>
"""
    path.write_text(page, encoding="utf-8")
    return path

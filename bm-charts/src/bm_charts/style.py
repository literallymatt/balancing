"""Matplotlib styling: the "Newsprint" look. Tinted paper, a serif headline
that states the finding, quiet gridlines and values on the right-hand axis.
Source Serif 4 for headlines, Source Sans 3 for everything else."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import httpx
import matplotlib as mpl
from matplotlib import font_manager

BACKGROUND = "#FFF1E5"
INK = "#33302E"
HEADING = "#1F1D1C"
MUTED = "#66605C"
SUBTLE = "#8A847F"
GRID = "#E6D9CE"
EVENT_BAND = "#F7DCC8"
EVENT_EDGE = "#A33E1E"

# Validated against the paper background for lightness, chroma and
# colour-blind separation. Blue = offers, red = bids throughout.
OFFER = "#2A6BAD"
BID = "#C4432F"

# Fixed order: a group keeps its colour whichever groups are present.
FUEL_COLOURS = {
    "Wind": "#2A6BAD",
    "Gas": "#C4432F",
    "Hydro and pumped storage": "#00A19A",
    "Interconnectors": "#8E6BBF",
    "Supplier and VLP units (incl. DSR)": "#D8902C",
    "Batteries": "#D9628F",
    "Other": "#B4AAA2",
}

TITLE_FONT = "Source Serif 4"
BODY_FONT = "Source Sans 3"
FONT_CSS = (
    "https://fonts.googleapis.com/css2?"
    "family=Source+Serif+4:wght@600&family=Source+Sans+3:wght@400;600"
)

# Canvas sized for the deck's 1664 x ~640 px content area, saved at 2x.
FIGSIZE = (16.64, 6.4)
DPI = 200


def ensure_fonts(font_dir: Path) -> None:
    """Download the Google Fonts once (as TTF) and register them.

    Each font set gets its own folder, so changing FONT_CSS fetches afresh.
    Falls back silently to the default sans if the download fails.
    """
    font_dir = font_dir / hashlib.sha1(FONT_CSS.encode()).hexdigest()[:10]
    font_dir.mkdir(parents=True, exist_ok=True)
    if not any(font_dir.glob("*.ttf")):
        try:
            css = httpx.get(FONT_CSS, timeout=30).text
            for i, url in enumerate(re.findall(r"url\((https://[^)]+\.ttf)\)", css)):
                (font_dir / f"font{i}.ttf").write_bytes(httpx.get(url, timeout=30).content)
        except httpx.HTTPError as exc:
            print(f"  could not download fonts ({exc}); using default sans")
    for path in font_dir.glob("*.ttf"):
        font_manager.fontManager.addfont(str(path))


def apply() -> None:
    mpl.rcParams.update(
        {
            "figure.facecolor": BACKGROUND,
            "axes.facecolor": BACKGROUND,
            "savefig.facecolor": BACKGROUND,
            "font.family": "sans-serif",
            "font.sans-serif": [BODY_FONT, "Arial", "DejaVu Sans"],
            "font.size": 15,
            "text.color": INK,
            "axes.labelcolor": MUTED,
            "axes.edgecolor": INK,
            "axes.linewidth": 1.2,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.spines.bottom": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 1.1,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelsize": 15,
            "ytick.labelsize": 15,
            "xtick.major.size": 0,
            "ytick.major.size": 0,
            "ytick.major.pad": 10,
            "xtick.major.pad": 8,
            "legend.frameon": False,
            "legend.fontsize": 14.5,
            "svg.fonttype": "path",
        }
    )


def heading_font() -> dict:
    # No fallback list: matplotlib warns about every listed family lacking 600.
    return {"fontfamily": TITLE_FONT, "fontweight": 600}

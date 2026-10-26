"""Matplotlib styling matched to the 'Margins, Constraints and the Case for
Flexibility' deck: cream background, navy ink, IBM Plex Sans body text and
Space Grotesk headings."""

from __future__ import annotations

import re
from pathlib import Path

import httpx
import matplotlib as mpl
from matplotlib import font_manager

BACKGROUND = "#F6F4EE"
INK = "#1B2638"
HEADING = "#14213D"
MUTED = "#4A5568"
SUBTLE = "#6B7280"
GRID = "#E2DDD0"
EVENT_BAND = "#FBE7D6"
EVENT_EDGE = "#B34D12"

# Validated against the deck background for lightness, chroma and
# colour-blind separation. Blue = offers, orange = bids throughout.
OFFER = "#2E6DB4"
BID = "#C8551B"

# Fixed order: a group keeps its colour whichever groups are present.
FUEL_COLOURS = {
    "Wind": "#2E6DB4",
    "Gas": "#C8551B",
    "Hydro and pumped storage": "#2A9D8F",
    "Interconnectors": "#8A5CB8",
    "Supplier and VLP units (incl. DSR)": "#C9961A",
    "Batteries": "#B8457A",
    "Other": "#9AA8BC",
}

FONT_CSS = (
    "https://fonts.googleapis.com/css2?"
    "family=IBM+Plex+Sans:wght@400;600&family=Space+Grotesk:wght@600"
)

# Canvas sized for the deck's 1664 x ~640 px content area, saved at 2x.
FIGSIZE = (16.64, 6.4)
DPI = 200


def ensure_fonts(font_dir: Path) -> None:
    """Download the deck's Google Fonts once (as TTF) and register them.

    Falls back silently to the default sans if the download fails.
    """
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
            "font.sans-serif": ["IBM Plex Sans", "Arial", "DejaVu Sans"],
            "font.size": 17,
            "text.color": INK,
            "axes.labelcolor": MUTED,
            "axes.edgecolor": INK,
            "axes.linewidth": 1.2,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.grid": True,
            "axes.grid.axis": "y",
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 1,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "xtick.labelsize": 16,
            "ytick.labelsize": 16,
            "ytick.left": False,
            "legend.frameon": False,
            "legend.fontsize": 16,
        }
    )


def heading_font() -> dict:
    return {"fontfamily": ["Space Grotesk", "IBM Plex Sans", "DejaVu Sans"], "fontweight": 600}

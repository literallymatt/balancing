# deck

Source files for the "Exploding cost of balancing the grid" slide deck
(about 20 minutes, for an I&C supplier audience). The deck lives as a Claude
Slides artifact; these files mirror its content so the slides and speaker
notes are versioned here alongside the analysis.

- `project/deck.json`: title, slide order and sections.
- `project/slides/<id>.html`: one slide each, with speaker notes in `<aside>`.
- `presenter-script.md`, `qa-prep.md` and `rnp-reforms-qa-brief.md`: speaker notes and Q&A prep.
- `fact-check-2026-11-02.md`: what the 2 Nov 2026 source check changed and what it couldn't verify.

Three slides embed charts from [`bm-charts/output/charts/`](../bm-charts/output/charts/),
uploaded to the artifact as images (the `/_blob/...` paths):

| Slide | Chart |
|---|---|
| `bmmonthly` | `01_monthly_bid_offer_costs.png` |
| `windbids` | `03_bid_payments_by_fuel.png` |
| `june23` | `05_focus_day_2026-06-23.png` |

If the charts are regenerated, re-upload the PNGs and update those `src` paths.
Annual cost figures (annual costs, wind bids and one-national-price slides) are calendar-year totals from NESO's Daily BSUoS Cost Data, produced by `uv run neso-costs` in bm-charts (`output/data/06_neso_annual_balancing_costs_calendar_year.csv`). Figures on the slides quoted from the BM data (for example £3.15bn paid out
Jan–Oct 2026) come from `bm-charts/output/data/` as of the 1 Nov 2026 run.

## Structure

1. The exploding cost: annual balancing costs, monthly BM payments
2. NESO's role: residual balancing, Gate Closure and FPNs, the BM toolkit
3. The difficulties: constraints, wind bid payments, one national price,
   invisible distributed assets, 23 June heatwave
4. The fixes: REMA and reformed national pricing, NESO's balancing reforms
5. Flexibility: how I&C DSR addresses each difficulty, customer opportunity

## PowerPoint version

`balancing-the-grid.pptx` is an editable PowerPoint export of the same slides,
built by `pptx/build.js`. It lays each slide out in headless Chromium and
rebuilds every box, border and text block as a native PowerPoint shape or text
box, so the text can be edited directly. The annual costs chart is a native
PowerPoint chart built from `data/annual_balancing_costs.csv` (forecast bars are
hatched with a dashed outline), and the tables are native PowerPoint tables.
Speaker notes come from each slide's `<aside>`, slides hidden in the HTML deck
are hidden in PowerPoint, and the PowerPoint sections follow `project/deck.json`.

Fonts are swapped to Arial, because IBM Plex Sans and Space Grotesk aren't
installed with Office. The HTML deck is unchanged and stays the source.

To rebuild after editing the slides:

```bash
cd deck/pptx
npm install       # needs Playwright with Chromium (npx playwright install chromium)
node build.js     # writes deck/balancing-the-grid.pptx
node build.js ../../deck-alt ../../deck-alt/balancing-the-grid-corporate.pptx   # the restyled copy
```

# deck

Source files for the "Exploding cost of balancing the grid" slide deck
(about 20 minutes, for an I&C supplier audience). The deck lives as a Claude
Slides artifact; these files mirror its content so the slides and speaker
notes are versioned here alongside the analysis.

- `project/deck.json`: title, slide order and sections.
- `project/slides/<id>.html`: one slide each, with speaker notes in `<aside>`.

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

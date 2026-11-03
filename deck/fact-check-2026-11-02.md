# Fact-check log, 2 November 2026

Every figure, date and threshold in the deck (`deck/`, `deck-alt/`, both pptx files) and the three
note files was checked against primary sources. Slide order is unchanged.

## What changed

**Local Constraint Market has closed.** From 7 October 2026 NESO buys constraint actions through
the Demand Flexibility Service, which replaced the LCM ([NESO DFS page](https://www.neso.energy/industry-information/balancing-services/demand-flexibility-service-dfs),
[LCM page](https://www.neso.energy/industry-information/balancing-services/local-constraint-market)).
The deck still offered the LCM as a live route. Fixed on slides 4, 14 (visible) and 16, 17, 18
(hidden), and in the script and Q&A.

**Demand for Constraints timing.** The deck said "tender this year, delivery from 2028". NESO
started procurement in October 2026; the invitation to tender is October 2027, contracts April 2028,
delivery from 2028. It's for new, additional flexible demand in Scotland (B2, B4, B5, B6), up to 10
years, and standalone batteries don't qualify
([NESO DfC webinar, 20 Oct 2026](https://www.neso.energy/demand-constraints-webinar-progress-implementation-20-october-2026)).
Fixed in slide 14's notes, the script and the Q&A.

**1 MW visibility applies to new generation only.** NESO's OTF table (28 Oct 2026) lists full BM
participation for existing post-G99 assets from 30 MW and new assets from 10 MW, and
visibility-only for "new generation assets only" from 1 MW. Batteries and CHP count; demand-only
sites under 10 MW don't. Slide 11 and slide 14 said "visible from 1 MW" without that caveat, and
slide 12 said 2032 brings "all assets above 1 MW in the BM". Fixed on slides 11, 12, 14 and in the
notes.

**June heatwave.** The deck said NESO managed "import constraints into the South East" and "cut
interconnector imports". NESO's preliminary report talks about "network constraints in the South
East of England", with both import and export restrictions on interconnectors (full export
restrictions on IFA2 and Eleclink, an Emergency Instruction to BritNed to stop exporting). It never
says "import constraint" or which way the SE flows ran. Slides 4 and 8 (notes) now say "network
constraints in the South East" and "interconnector limits". The hidden site example (slide 17) now
uses southern England with the Scottish boundaries full as its "in front of a constraint" case.

**Smaller fixes**
- Slide 5 notes: trading runs to Gate Closure (with P342 notifications after), not "an hour before
  delivery" as a hard stop.
- Slide 7 notes (hidden): dropped the unverifiable claim that NESO's order of actions treats DFS as
  "cost-based alongside BM offers". It now says DFS has been a year-round tool since November 2024.
- Slide 9 (hidden): 56% is non-BM *generation* at peak sunny, windy times *in 2025*; the frequency
  spend tripled to £8.87m a month by *October 2025* (the note said "last October", which now reads
  as 2026); the 2 GW of NIV chasing came from sources NESO can't see.
- Slide 10 (hidden): "decisions from late 2026; first reforms from 2027" is out of date. Now
  "NESO recommends Dec 2026; decision in 2027; first changes from 2029".
- Slides 14 and 17: the £121 to £245/MWh doubling is all accepted BM offers, not just gas offers.
- Q&A: P342 dates (raised May 2016, approved 1 Feb 2017, live 2 Nov 2017); P344 and P415 dates
  (P415 live 7 Nov 2024, so the [check] is resolved); STOR procurement ended 31 March 2026 and Slow
  Reserve replaced it; Quick Reserve phase 1 live 19 Nov 2024 with full delivery in 1 minute;
  Balancing Reserve from March 2024; SSEP is a draft in early 2027 and final in autumn 2027 (not end
  of 2026); GTMA is the market's standard master agreement, which NESO signs with each
  counterparty; skip-rate figures added; removed the unverified "Constraints Management Action Plan"
  name.
- RNP brief: 1 MW visibility caveat; current thresholds (NESO uses 50/30/10 MW; the Grid Code's
  E&W large power station threshold is 100 MW); unit-level bidding status reworded to NESO's July
  wording; P342 and SDAC dates added. The brief now also lives in the repo at
  `deck/rnp-reforms-qa-brief.md`.

## Checked and correct

- Annual costs chart: *superseded 3 Nov 2026.* The chart now uses NESO's MBSS (headline) basis rather
  than the daily BSUoS data, which ran about a quarter below NESO's published totals. See
  `bm-charts/output/data/07_neso_mbss_annual_calendar_year.csv` and `deck/data/annual_balancing_costs.csv`:
  2026 ≈ £3.4bn to end Oct + £0.83bn forecast ≈ £4.3bn; 2027 = £4.15bn; 1.9× 2020 to October;
  constraints 70% of 2025.
- £2.7bn for 2024/25, ~£8bn peak in 2030 and ~£4bn saving if critical projects are brought
  forward: NESO 2025 Annual Balancing Costs Report, pp.18 and 24.
- BM figures from our Elexon data: £3.15bn Jan–Oct 2026 vs £2.33bn in all of 2025; £121 → £245/MWh
  (Oct 2025 → Oct 2026); wind 94%, supplier and VLP units 0.3% of bid payments.
- Grid Code BC1: initial PNs by 11:00 day ahead; no PN or bid-offer changes after Gate Closure;
  dynamic parameters can still be redeclared.
- P342 lets ECVNs and MVRNs run to the start of the settlement period; NESO's reform would reverse it.
- RNP: CfI Feb 2026 (closed 14 Apr), 81 responses, IEP from April 2026, 15-minute base case, Q1 2029
  first go-live, phases 2029/2030/2032, settlement 2032/2035, Ofgem and the Secretary of State
  decide, NESO recommends to DESNZ and Ofgem.
- DFS: 0.1 MW minimum, turn-up, 12 zones from 9 April 2026; announced 25 March 2026.
- REMA from 2022; zonal pricing ruled out July 2025; RNP delivery plan 21 April 2026 with three
  components and the levy trial for constrained parts of Scotland and the East of England.
- BSUoS on demand only and fixed tariffs since April 2023; 15-minute EU day-ahead products (SDAC from
  30 Sept 2025; 80+% adoption by Jan 2026); Australia 5-minute settlement Oct 2021; G99 Type B 1–10 MW.

## Couldn't fully verify

- NESO's OTF slide 20 extracts without its table layout, so which reform each "Q1 2029 go-live"
  label belongs to isn't certain. The deck's "Q1 2029 first go-live" date is right either way.
- The levy-free trial: the delivery plan says constrained parts of Scotland and the East of England,
  but the £20m UKRI trial material published in October doesn't name its areas.
- The 0.3% "demand" share is the supplier and VLP category, which includes some non-demand units.
- Eastern Green Link and ASTI project dates are still marked [check] in the Q&A.
- Appendix C of the heat review (NESO's order of actions) wasn't readable, so the toolkit slides
  cite it only for the tool list, which matches section 5.7.
- "Tight days in December and January" (hidden slide 20) wasn't checked against NESO's Winter
  Outlook.

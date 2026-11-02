# Q&A prep: Balancing the grid

Likely questions for the talk, grouped by theme, with a short answer to lead with and the detail behind it. Slide numbers use the deck's own numbering.

**How to read this**
- **Say:** the one or two sentences to open with.
- **If pressed:** the detail, only if they push.
- **[check]** marks points that come from general industry knowledge rather than the deck's sources. They're right to the best of my knowledge, but confirm before quoting a specific date or number, or answer with "my understanding is…".
- For the five RNP reforms in depth, `notes/rnp-reforms-qa-brief.md` in the project files has the full reasoning and sources.

**General tactics**
- If you don't know: "Good question. I don't want to guess, so I'll come back to you on that." Then write it down.
- If a question drifts into our commercial terms or pricing for a specific customer, take it offline.
- Bring every answer back to one of the three columns on slide 14 (peak, constraints, visibility) where you can.

---

## 1. The cost numbers (slide 3)

### Why do your numbers differ from NESO's headline figures?
**Say:** We use NESO's daily BSUoS cost data because it's the only NESO series we can cut into calendar years. It covers fewer cost lines than the annual balancing cost reports, so it sits a bit lower.
**If pressed:** For 2024/25 it's about £2.1bn on our basis against £2.7bn in NESO's report. The trend is the same on either basis.

### Why is there a gap for 2028 and 2029?
**Say:** NESO hasn't published annual forecasts for those years. Rather than invent numbers, I've left them blank.
**If pressed:** 2026 (Nov and Dec) and 2027 come from NESO's October 2026 BSUoS forecast. 2030 is from NESO's 2025 Annual Balancing Costs Report. The bases differ from our actuals, so treat the orange bars as direction of travel.

### What drove the 2022 spike, and is 2026 the same?
**Say:** No. 2022 was a price spike: gas crisis prices made reserve and other services expensive. 2026 is a volume and location problem: nearly all of it is constraints.

### Is the £8bn by 2030 realistic?
**Say:** It's NESO's own projection, not ours. It's driven by wind connecting faster than the network is reinforced, and NESO says around £4bn of it is avoidable if critical network projects are delivered earlier.
**If pressed:** That's why network build timing (see section 7) is the biggest swing factor.

### What does this mean for our customers' bills?
**Say:** BSUoS has fallen entirely on demand since April 2023, so every pound of balancing cost is passed through to suppliers and on to customers.
**If pressed [check]:** BSUoS is now a fixed tariff set in advance for each period rather than a volatile ex-post charge, which helps customers budget but means overruns come back in later tariffs. Don't quote a £/MWh figure unless you've checked the current NESO tariff.

---

## 2. Gate Closure, P342 and trading (slides 5, 6, 11)

### If the market can trade until the start of the half-hour, why do you say Gate Closure is when NESO takes over?
**Say:** Two different things lock at different times. Physical plans (FPNs) and BM prices lock at Gate Closure, an hour ahead. Since P342 in 2017, contract notifications to Elexon can keep going until the start of the period. Those late trades change who's long or short for settlement, but they can't change what units physically do, because NESO is already working from the locked FPNs.
**If pressed:** P342 was raised by EDF in 2016 and approved by Ofgem in February 2017, to let parties use better forecasts nearer real time and to support intraday liquidity.

### Why does NESO want to reverse P342?
**Say:** So that the physical plan and the traded position are fixed at the same moment. At the moment the last hour of trading is invisible to NESO's planning.
**If pressed:** NESO's own wording is that "traders will need to finalise trades earlier and manage higher imbalance risk". It's one of the two reforms industry pushed back on hardest. NESO is studying trading behaviour before and after P342 but hasn't published results.

### Wouldn't that hurt wind and suppliers?
**Say:** Yes, it's the main cost. The last hour mostly helps parties with uncertain output, like wind, and suppliers whose demand forecasts sharpen close to real time. That's why it's one of the less certain reforms.
**For us [inference]:** As a supplier we'd carry more imbalance risk on our own demand forecast, which is another reason flexible customer load is valuable to us as well as to NESO.

### What's NIV chasing?
**Say:** Deliberately running long or short into the imbalance price, betting on which way the system will be out. NIV is the net imbalance volume.
**If pressed:** NESO linked around 2 GW of it on one day in November 2025 to frequency oscillations. But its own control room has also said "BMU physical NIV chasing is not a key system operation challenge", so the FPN-matching reform is the least certain of the five.

---

## 3. FPNs and supplier BM units (slides 5, 6)

### Do suppliers submit FPNs?
**Say:** Every BM unit has an FPN. Our customers' demand sits in supplier "base" BM units, one per supplier per GSP group, but those generally aren't actively bid into the BM, so in practice the FPN regime bites on generators, batteries, interconnectors and registered flexible units.
**If pressed [check]:** Supplier demand is settled on metered volumes against our contracted position, and imbalance is cashed out by Elexon. A supplier can register additional BM units to put specific flexible sites into the BM.

### What exactly is "locked" at Gate Closure?
**Say:** The FPN, and the bid and offer prices for that period. What can still change are the unit's dynamic parameters: MEL, MIL, ramp rates and notice times, so a unit can tell NESO if a fault changes what it can do.

### What's the difference between MEL and MIL?
**Say:** Maximum Export Limit is the most a unit can put onto the system; Maximum Import Limit is the most it can take off. Offers run from the FPN up to MEL; bids run from the FPN down to MIL.

---

## 4. How NESO trades and buys services (slides 4, 5)

### What are GTMA and PGBT trades?
**Say:** Both are ways NESO trades ahead of Gate Closure rather than in the BM. GTMA trades are made under the Grid Trade Master Agreement, the standard bilateral framework NESO uses with counterparties. They can be plain energy trades or tied to specific units, which is how NESO does locational constraint trades.
**If pressed [check]:** PGBTs (pre-gate balancing transactions) are a related pre-Gate Closure contract type. If someone wants the precise contractual difference, offer to follow up rather than improvise. The point for the talk is that these trades let NESO fix some problems earlier and often more cheaply than in the BM.

### How do interconnectors fit in, and why can't NESO just use them intraday?
**Say:** Interconnectors are part of both energy and system balancing. NESO can trade across them and do system-operator-to-system-operator trades, and in the June heatwave it cut imports into the South East because of local network limits.
**If pressed [check]:** Since GB left the EU internal energy market, interconnector capacity is allocated through explicit auctions rather than implicit market coupling, which makes intraday cross-border trading clunkier. Europe has also moved to 15-minute products (over 80% of EU day-ahead trading by January 2026), so GB at 30 minutes is out of step at the borders. That's part of NESO's case for 15-minute settlement.

### What are Balancing Reserve, Quick Reserve, Slow Reserve and STOR?
**Say:** They're NESO's reserve products: capacity it pays to hold back so it can call on it fast if something goes wrong.
**If pressed [check]:**
- **Balancing Reserve:** procured day ahead, pays BM units to keep headroom so they can deliver offers (or bids) in real time. Launched in 2024, mainly to reduce the need to warm gas plant through the BM.
- **Quick Reserve:** fast reserve that must respond within about a minute, both upward and downward. Part of NESO's reformed reserve suite.
- **Slow Reserve:** reserve within about 15 minutes, positive and negative. It's the successor to STOR.
- **STOR (Short Term Operating Reserve):** the older reserve product, historically popular with I&C sites and diesel or gas peaking plant. Being phased out in favour of Slow Reserve.
- **For customers:** reserve products are availability payments and can stack with other routes. Sites with batteries or fast controls are the natural fit for Quick Reserve.

### What's the Demand Flexibility Service now?
**Say:** It started as a winter scheme for households, but it was redesigned in 2026. The minimum size dropped from 1 MW to 0.1 MW, it pays for turn-up as well as turn-down, it's procured by zone, and since October it buys constraint actions too. NESO's own order of actions now treats it as an everyday, cost-based tool alongside BM offers.

---

## 5. VLPs, the BM and skip rates (slides 6, 14)

### Can demand actually turn down in the BM today?
**Say:** Yes, through a Virtual Lead Party: an aggregator or supplier registers flexible sites into a secondary BM unit and bids and offers them like a generator. A demand site turning down is an offer; turning up is a bid.
**If pressed [check]:** VLP access to the BM came in through BSC change P344 in 2019. P415 extends VLP access into the wholesale market. Check the current P415 go-live status before quoting a date.

### If demand can already do it, why does demand only get 0.3% of turn-down money?
**Say:** Mostly scale and location. Wind farms are large, already in the BM and sit exactly behind the constraint. Most flexible demand is small, below the threshold, and not set up to bid. That's the gap the Demand for Constraints market and lower thresholds are meant to close.
**If pressed:** Wind gets about 94% of the turn-down money (our analysis of Elexon BMRS data). That's the size of the opportunity for demand to compete.

### What are skip rates, and won't small sites just get skipped?
**Say:** A skip is when NESO's control room passes over a cheaper bid or offer and takes a more expensive one. Sometimes that's for good reasons (wrong location, too slow, can't run long enough), and sometimes it's because control room tools couldn't handle lots of small units.
**If pressed [check]:** Batteries in particular complained of being skipped. NESO now publishes skip rate data and has been rolling out its Open Balancing Platform to dispatch many small units at once. The honest answer for customers: skip risk is real, and being well located, reliable and fast is what reduces it. That's also what slide 6 says about how NESO picks.

---

## 6. The reforms and timeline (slides 11, 12)

Full detail is in `notes/rnp-reforms-qa-brief.md`. The quick answers:

### Why 10 MW, and why 30 MW for existing sites?
**Say:** At 10 MW, NESO says, BM revenues may not cover the cost of the control, metering and trading kit. Retrofitting existing sites costs more, so the bar is higher for them, and it only applies to sites connected under G99 (2019 onwards).
**If pressed [inference]:** 30 MW and 10 MW are today's southern and northern Scotland thresholds, so in effect the Scottish levels would go GB-wide. 1 MW matches the G99 Type B boundary.

### Why 15 minutes and not 5?
**Say:** NESO calls 15 minutes "the more proportionate first step". It matches Europe, and 5 minutes would need much more automated trading and metering. Australia went to 5 minutes in 2021, if anyone cites it.
**Knock-on:** the BM window per period would shrink from about 90 minutes to about 75, which is awkward for slow gas plant.

### When will any of this actually happen?
**Say:** NESO recommends in December 2026; Ofgem and the Secretary of State decide, realistically in 2027. If approved, the first go-live is Q1 2029 and the main changes land in 2032.

### Will our customers be forced into the BM?
**Say:** Not soon. On NESO's plan, new assets over 30 MW join from 2029 and over 10 MW from 2030. All assets over 1 MW, including existing ones, come in from 2032, and below 10 MW that's visibility, meaning data to NESO, rather than full bidding. How far back the rules reach for existing sites is still open.

### Does any of this remove constraints?
**Say:** No, and NESO says so itself. These reforms make redispatch cheaper to manage. The real fixes are building network and putting new assets in the right places, which sit in the other RNP pillars.

---

## 7. Network build and the bigger picture (slides 3, 8)

### Why not just build more network?
**Say:** That's the real fix, and it's happening, but it takes years. NESO's £4bn of avoidable cost by 2030 depends on critical projects coming forward. Flexibility is what fills the gap until then, and helps around the edges afterwards.
**If pressed [check]:** The big ones are new subsea HVDC links from Scotland to England (the Eastern Green Links) and onshore reinforcement under Ofgem's accelerated transmission programme (ASTI), mostly due late this decade into the early 2030s.

### What's the SSEP?
**Say:** The Strategic Spatial Energy Plan, led by NESO. It maps where generation, storage and demand should go across GB, so network and new assets are planned together. It's part of the first RNP pillar: build in the right places.
**If pressed [check]:** The first full SSEP is expected around the end of 2026. Check the latest NESO date before quoting.

### Why did government rule out zonal pricing?
**Say:** In July 2025 it kept a single national price, citing risks to investment and delivery, and chose Reformed National Pricing instead. The REMA slide is hidden today, so keep this to a sentence unless they push.
**If pressed:** RNP has three pillars: get assets built in the right places (SSEP, connections reform, locational network charges); cut constraint costs (network build, the levy-free demand trial); and reform balancing (NESO's five reforms).

### What's the Constraints Management Action Plan and Demand for Constraints?
**Say:** NESO's programme of measures to bring constraint costs down. For us the important piece is the Demand for Constraints market: a longer-term contract for demand that can turn up in constrained areas, tendering this year for delivery from 2028.
**If pressed [check]:** Alongside it sit the Local Constraint Market (flexible sites behind the Scotland to England boundary, already running) and government's trial removing final consumption levies for demand in constrained parts of Scotland and the East of England, so sites there can get cheap or free power when wind is surplus. Confirm the exact action-plan name and tender dates against NESO's latest page before quoting.

### Isn't this mainly a Scotland problem? Most of our customers are in England.
**Say:** Scotland is the classic case, but not the only one. In the June 2026 heatwave NESO was managing import constraints into the South East. Sites in front of a constraint help by turning down; sites behind one help by turning up. And the peak and visibility value on slide 14 applies anywhere.

---

## 8. The customer opportunity (slide 14)

### What can a customer actually sign up to today?
**Say:** Four routes, and they stack:
1. **DFS:** now from 0.1 MW, turn-up and turn-down, zonal, and buying constraint actions.
2. **The BM through a VLP:** earn the same bid and offer prices as generators.
3. **Availability payments:** the Capacity Market for peak reduction, and reserve and response markets for fast sites.
4. **Avoided costs:** not consuming at the peak cuts wholesale, imbalance and red-band network charges.

### How much could a site earn?
**Say:** It depends on size, location, how fast it can respond, and how often it can move without hurting the process. I'd rather not give a number without looking at the site's data. Happy to run that analysis.
**Anchor if needed:** the average accepted BM offer price roughly doubled over the past year, from about £121 to £245/MWh (our analysis).

### Won't flexing disrupt production?
**Say:** Only if it's set up badly. The best candidates are loads with some slack: thermal storage, pumping, refrigeration, batch processes, or on-site generation and batteries. Customers set the limits and can decline events in most schemes.

### Why should a customer act now if the reforms don't land until 2029 to 2032?
**Say:** Because the money from DFS, the BM, reserve and constraints is available today, and because sites that are already metered and controllable will be first in line when thresholds drop. Getting ready late means competing with everyone else at once.

### What's in it for us as a supplier?
**Say:** Better customer retention and value, and a hedge on our own position: flexible load helps us manage imbalance risk, which matters more if the trading deadline moves back to Gate Closure.

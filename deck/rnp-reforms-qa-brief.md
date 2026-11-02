# RNP balancing reforms: Q&A brief

Speaker prep for slide 11 (reforms) and slide 12 (timeline). This brief reflects NESO material up to the 28 Oct 2026 OTF pack, and was fact-checked against the sources below on 2 Nov 2026. Statements marked **[inference]** are my reasoning and do not appear in NESO's documents. If you're asked about one of those, frame it as "my understanding is…".

## 1. Lower BM participation threshold

**What it fixes.** Today, only large plant has to take part in the Balancing Mechanism. NESO's IEP pre-read uses 50 MW in England and Wales, 30 MW in southern Scotland and 10 MW in northern Scotland to segment assets. Exactly where the obligation bites in England and Wales depends on licence and connection type: the Grid Code's "large power station" threshold there is 100 MW, while licensed plant from 50 MW generally has to register BM units. A growing share of capacity sits below that, mostly batteries, solar and flexible demand connected to distribution networks. NESO can't see those assets or dispatch them directly. NESO says it "has limited visibility of non-BMU assets" and wants access to "a sufficiently large and valuable pool" of distribution-connected assets. When NESO can't see an asset, it has to forecast around it and hold more margin, and it can't pick that asset for its location when there's a constraint.

**What's proposed.** Full BM participation for existing assets from 30 MW (those connected under G99) and new assets from 10 MW, and visibility only (data, no bidding) for new generation assets from 1 MW. NESO's October table says "new generation assets only" for the 1 MW tier, so demand-only sites below 10 MW aren't caught; batteries and CHP count as generation. This is phased in: new assets over 30 MW from 2029, new over 10 MW from 2030, and all over 1 MW plus retrospective application from 2032.

**Why those numbers.**
- **10 MW floor:** NESO's own reason is cost. Near 10 MW, "BM revenues may not cover the CAPEX to implement and OPEX to trade". Below that size, the control systems, metering and trading cost more than an asset could earn in the BM.
- **30 MW for existing assets:** retrofitting existing sites costs more than building the capability into new ones, so the bar is set higher, and it only applies to sites already connected under G99 (2019 onwards). Those sites already have modern, compliant controls. NESO lists "level of retrospectivity: threshold and how far back" as still open.
- **[inference]** 30 MW and 10 MW are the existing southern and northern Scotland thresholds. In effect, the proposal extends the Scottish levels GB-wide, which would remove the long-standing quirk that a 40 MW plant is in the BM in Scotland but not in England.
- **[inference]** 1 MW matches the G99 "Type B" boundary (1 to 10 MW). Type B assets already have to provide some operational data, so 1 MW is a natural floor for visibility.

## 2. Shorter settlement period

**What it fixes.** Imbalance is currently settled over 30 minutes, which blurs what happens within each half-hour. A site that overshoots for 15 minutes and undershoots for 15 can net to zero and pay nothing, even though NESO had to balance both swings. Shorter periods make price signals sharper, so fast and accurate response gets rewarded.

**What's proposed.** 15 minutes as the base case, with 5 minutes tested as a sensitivity. It would apply from 2032 for the wholesale market and large sites with Code of Practice metering, and from 2035 for homes and small businesses.

**Why 15, not 5.** NESO calls 15 minutes "the more proportionate first step". It also matches Europe: the EU day-ahead market moved to 15-minute products on 30 September 2025, and NESO puts adoption at over 80% of EU day-ahead trading by January 2026, so GB at 30 minutes is now out of step at the interconnectors. Five minutes would need what NESO calls "a move towards algorithmic and automated trading". **[inference]** It would also put more strain on meters and settlement systems. Australia moved to 5-minute settlement in October 2021 and is the example people usually cite.

**Why 2032 and 2035.** Settlement follows the meters. Large sites already have half-hourly Code of Practice meters, so they can go first. Homes and small businesses need meter upgrades, which NESO expects to be done by 2035. **[inference]** This follows on from the market-wide half-hourly settlement programme (MHHS), which is completing now.

**Knock-on effect.** The BM window for a period runs from Gate Closure to the end of the period, so it would shrink from about 90 minutes to about 75. Slow plant such as CCGTs, which can need 60 to 89 minutes' notice, would need mitigations that haven't been designed yet.

## 3. Trading stops at Gate Closure (reversing P342)

**What it fixes.** Since P342 went live on 2 November 2017, parties can keep trading and notify contracts to Elexon until the start of the period, which is an hour after FPNs lock. So the physical plan NESO sees at Gate Closure isn't the final market position, and the trades made in that last hour are invisible to NESO's planning. Moving the deadline back to Gate Closure means FPNs and contracts are fixed at the same moment.

**Why it's controversial.** Traders lose an hour to fine-tune their positions. NESO's own wording is that "traders will need to finalise trades earlier and manage higher imbalance risk". The hour mostly helps parties with uncertain output, such as wind, and suppliers whose demand forecasts improve close to real time. NESO is studying trading behaviour before and after P342, but hasn't published results.

**Why P342 happened in the first place.** EDF Energy raised it in May 2016 to let parties trade nearer real time, using better forecasts, and to give liquidity to the intraday market. Ofgem approved it on 1 February 2017. NESO's Call for Input adds that it was recognised at the time that P342 could also encourage some parties to change position after Gate Closure.

## 4. FPNs must match traded positions

**What it fixes.** Today a BM unit's FPN doesn't have to equal what it has sold. A party can deliberately run long or short into the imbalance price, betting on which way the system will be out (this is called NIV chasing). It also leaves NESO with a plan that doesn't add up. The rule would make the FPN equal the contracted position, with aggregated positions shared with NESO before Gate Closure.

**What's proposed.** Matching at portfolio level, using Elexon account positions, FPNs, non-BM metered data and forecast deviations, within tolerances. The tolerances will be consulted on in 2027–28.

**Why tolerances and portfolio level.** Forecast error is unavoidable for wind, solar and demand, so exact matching would penalise honest mistakes. Checking at portfolio level lets one unit's error offset another's, which reflects how parties actually trade and keeps the compliance burden manageable. NESO hasn't set any tolerance values yet.

**Caveat if challenged.** NESO's own control room has said that "BMU physical NIV chasing is not a key system operation challenge", and industry pushed back hard on this reform. So it's the least certain of the five to go ahead.

## 5. Unit-level bidding and dispatch reform

**What it fixes.** Most wholesale trading happens at portfolio level, so a trade doesn't say which plant, and therefore which location, will deliver it. Unit-level bids in the day-ahead and intraday markets would tie each trade to a specific unit. That supports FPN matching and gives NESO a clearer locational picture before Gate Closure. Dispatch reform would go further, giving NESO more say over which units run, with the aim of fitting schedules to the network.

**Where it stands.** NESO isn't running a full cost-benefit analysis on unit-level bidding at this stage; it will first size the inefficiency from strategic behaviour, and its IEP pre-read notes gaps in the analysis due to "reprioritization of the reform". It will recommend on unit-level bidding and dispatch reform together at the end of 2027 (July feedback summary), after a separate Call for Input on dispatch. NESO's IEP page says dispatch proposals "will be shared with industry in due course". Both reforms were the least popular in the Call for Input, because they move GB away from self-dispatch, which is the basic design of the GB market.

## The big caveat for Q&A

NESO says these reforms make redispatch cheaper to manage but don't remove the congestion that causes it. Building network and locating assets in the right places are the real fixes, and they sit in the other RNP pillars.

## Sources
- NESO RNP Industry Expert Panel page (reform list, IEP meetings): https://www.neso.energy/industry-information/reformed-national-pricing/rnp-industry-expert-panel-iep-balancing-settlement-dispatch-reforms
- NESO Operational Transparency Forum slides, 28 Oct 2026, RNP section (thresholds, timeline, decision process): https://www.neso.energy/document/389296/download
- IEP 5 pre-read, for the 8 Sept 2026 meeting (10 MW cost rationale, 15 vs 5 minutes, 2032/2035 metering, the 90 to 75 minute window, the ENCC view on NIV chasing): https://www.neso.energy/document/386741/download
- Elexon P342: https://www.elexon.co.uk/mod-proposal/p342/
- NESO RNP Call for Input (Feb 2026): https://www.neso.energy/document/376966/download, and feedback summary (Jul 2026, 81 responses): https://www.neso.energy/document/384331/download

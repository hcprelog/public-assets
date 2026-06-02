# HC-SOP-001 — GovCon Bid & Vendor Sourcing Process
Version: 1.0 | Created: 2026-06-02 | Owner: President Hunter

---

## PURPOSE
Define the mandatory end-to-end process from opportunity identification through sub/vendor engagement for every contract H&C pursues. H&C primes — subs execute. No bid proceeds without a viable execution sub identified first.

---

## MANDATORY SEQUENCE — NEVER SKIP STEPS

```
STEP 1: OPPORTUNITY IDENTIFIED (SAM.gov scan)
         ↓
STEP 2: INITIAL TRIAGE (bid/no-bid score ≥7/10)
         ↓
STEP 3: SUB/VENDOR SEARCH (BEFORE any CO contact)
         ↓
STEP 4: SUB CANDIDATE SHORTLIST (min 2 candidates)
         ↓
STEP 5: PRESIDENT HUNTER APPROVAL [DECISION NEEDED]
         ↓
STEP 6: SUB OUTREACH (use HC-SUB-OUTREACH template)
         ↓
STEP 7: SUB CONFIRMED — verbal commit minimum
         ↓
STEP 8: PRICE BUILD (sub cost + H&C markup 10-12%)
         ↓
STEP 9: PROPOSAL / QUOTE SUBMITTED
         ↓
STEP 10: AWARD TRACKING → HubSpot update
```

---

## STEP 2: BID/NO-BID SCORING (0-10 scale)

| Factor | 0 pts | 1 pt | 2 pts |
|---|---|---|---|
| NAICS match | Not in H&C SAM | Related but not exact | Exact match in SAM registration |
| Past performance | None relevant | Related PP | Same agency or same work type |
| Competition | Open market, many bidders | SDVOSB/HUBZone competitive | Sole source or thin competition |
| Value range | <$5K or >$1M | $5K–$25K or $250K–$1M | $25K–$250K sweet spot |
| Agency relationship | No prior contact | Researched, no contact | Prior contract or CO relationship |

**Threshold:** ≥7 = Pursue | 5–6 = Pursue if sub found fast | <5 = Pass

---

## STEP 3: SUB/VENDOR SEARCH PROTOCOL

### Primary Sources (in priority order)

**1. H&C NAICS Vendor Library** (check first — free)
- `/govcon/vendors/naics-[code]-subs.md`
- If a vetted sub exists for that NAICS + region → go to Step 4

**2. SAM.gov Entity Search** (free, government-verified)
- Log into sam.gov → Search → Entity Registration
- Filter: NAICS Code = [target code] | State = [PoP state] | Status = Active
- Target: Small businesses (1-50 employees), NOT SDVOSB (they'd compete directly)
- Save all candidates to the relevant NAICS vendor file

**3. Apollo.io Company Search** (1 credit per search)
- Search: courier/logistics/[service type] + [city/state]
- Filter: 1-50 employees, no VC funding (hungry for revenue)
- Get owner/president contact info

**4. Google Maps / Local Directories** (free)
- Search: "[service type] [city, state]"
- Look for companies with: reviews but not huge, local only, 2-15 years old
- These subs didn't win the set-aside because they're not SDVOSB — H&C gives them revenue they couldn't get alone

**5. LinkedIn** (free)
- Search company type + location
- Find owner/president direct

---

## STEP 4: SUB CANDIDATE EVALUATION CRITERIA

Target profile — the ideal execution sub:
- ✅ In the right geographic area (within 50 mi of PoP)
- ✅ Has the physical capability (vehicles, staff, equipment)
- ✅ Small enough to appreciate the revenue (1-50 employees preferred)
- ✅ Not currently winning SDVOSB set-asides on their own
- ✅ SAM.gov registered OR willing to register (H&C assists)
- ✅ Owner reachable directly (not gated by a large corporation)

---

## STEP 6: SUB OUTREACH — MESSAGING FRAMEWORK

**Opening hook** (what to say in first 30 seconds / first email sentence):
> "Hi [Name], I'm Dennis Hunter, President of H&C Precise Logistics — we're an SDVOSB and HUBZone certified company and we just identified a [Agency] contract opportunity that's set aside for veteran-owned businesses. We're looking for a local [service] company in [city] to be our execution partner. We win the contract, you do the work, we pay you on Net 30. Interested in a 15-minute call?"

**Key points to cover:**
1. H&C holds the prime contract + handles all compliance/billing
2. Sub does the work in their area — no contracting overhead for them
3. H&C markup is NEVER disclosed — present sub's rate as the rate
4. Net 30 payment from H&C once government pays
5. If not SAM-registered, H&C walks them through it (free)
6. Long-term: recurring VA contract work if performance is good

**What NOT to say:**
- Never mention H&C markup percentage
- Never imply the sub could have won this directly (they couldn't — SDVOSB set-aside)
- Never commit to specific dollar amounts until pricing is built

---

## STEP 8: PRICE BUILD (internal only — never show to sub)

```
Sub quoted rate:     $X
H&C markup (10-12%): $X × 1.12
= H&C bid price:     $Y  ← This is what goes in the proposal
```

Markup is NEVER disclosed externally. Sub sees only: "H&C will pay you $X per [unit/month/trip]."

---

## VENDOR LIBRARY STRUCTURE

All subs saved to: `/govcon/vendors/naics-[code]-subs.md`

Current vendor files:
- `/govcon/vendors/naics-492110-courier-subs.md` — Lab/medical couriers
- `/govcon/vendors/naics-484110-freight-subs.md` — Local freight trucking
- `/govcon/vendors/naics-561720-janitorial-subs.md` — Janitorial (future)
- `/govcon/vendors/naics-561210-facilities-subs.md` — Facilities support (future)

---

## NOTES
- govcon-opportunity-triage MUST run before any vendor contact (per CLAUDE.md)
- No vendor contact without packaged one-page Opportunity Summary
- Log every outreach attempt in the relevant NAICS vendor file
- Good subs = recurring relationship — treat them like partners

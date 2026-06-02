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

## STEP 3: SUB/VENDOR SEARCH PROTOCOL — TWO-TIER STRATEGY

### Tier 1 — Execution Subs (NOT SAM/government registered) — PRIORITY
**H&C's pitch:** "We win government contracts you can never access on your own. You do the work in your area. We pay you Net 30."
- Target: Owner-operated, 1-50 employees, local/regional, no government contracting history
- Why they say YES: New revenue channel they can't open themselves
- H&C leverage: Maximum — they have zero path to this work without H&C
- Ideal profile: Already doing medical/lab/facility work for private clients, just not federal

### Tier 2 — Consulting Clients (SAM registered, not winning) — SECONDARY REVENUE
**H&C's pitch:** "You're registered but not winning. You don't have SDVOSB or HUBZone. We do. Buy our GROWTH ($297/mo) or PRIME READY ($797/mo) plan — we team with you on bids AND teach you how to build your own pipeline."
- Target: SAM-registered small businesses struggling to win set-aside contracts
- Why they say YES: They're paying for SAM registration and getting nothing from it
- Revenue: Subscription + potentially sub on bids while they learn
- Long-term: H&C alumni who refer others

### Search Sources (Tier 1 priority)
1. `/govcon/vendors/naics-[code]-subs.md` — Check existing library first (free, instant)
2. Web search: "[service type] [city, state] small business owner operated" — find companies with no government footprint
3. Google Maps/Yelp: Local service companies in target city — call directly
4. LinkedIn: Owner/president of small local service companies
5. SAM.gov entity search (browser): For Tier 2 prospects — registered but not winning

### Never target
- Large national companies (they don't need H&C)
- Companies with active SDVOSB/HUBZone certs (they compete directly)
- Companies that already have VA or DOD prime contracts

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

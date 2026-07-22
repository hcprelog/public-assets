# Weekly GovCon Opportunity Scan — 2026-06-01
Role: govcon-capture-analyst
Analyst: Claude Code (automated)
Date: 2026-06-01
Status: **BLOCKED — SAM.gov API key required**

---

## SCAN PARAMETERS

| Parameter | Value |
|---|---|
| NAICS Codes | 484110, 493110, 541614, 488510, 492110 |
| Set-Aside Priority | SDVOSB (primary), HUBZone (accepted), 8(a) (flag for teaming only) |
| Value Range | $5,000 – $500,000 |
| Posted Window | 2026-05-25 → 2026-06-01 (last 7 days) |
| Opp Types | Solicitation (o), Pre-Solicitation (p), Combined (k), Sources Sought/RFI (r) |
| Exclude | 36C25925P1197 (VA Hazardous Waste — stable, active) |

---

## PLATFORMS ATTEMPTED

| Platform | Result | Notes |
|---|---|---|
| SAM.gov API (api.sam.gov/opportunities/v2/search) | ❌ 403 Forbidden | DEMO_KEY rejected. Requires registered API key. |
| SAM.gov opportunity pages (direct URL) | ❌ 403 Forbidden | All individual opp pages blocked without session auth. |
| DIBBS (dibbs.dla.mil) | ❌ ECONNREFUSED | DLA site blocks external fetches. |
| Unison Marketplace | ❌ 403 Forbidden | Requires account/session. |
| Bonfire | ❌ No relevant results | No federal logistics/transportation opps matching NAICS. |
| HigherGov, SamSearch, GDIC | ❌ 403 Forbidden | All third-party aggregators block unauthenticated access. |

---

## PARTIAL DATA (web search fragments — insufficient for triage)

| Solicitation | NAICS | Set-Aside | Value | Status | Notes |
|---|---|---|---|---|---|
| VA/NAICS 492110 (unnamed) | 492110 | SDVOSB | Unknown | ❌ EXPIRED | Response deadline was 2026-02-17. Cannot act. |
| SP30026R5003 | 493110 | SDVOSB | ~$88M | ❌ TOO LARGE | Exceeds $500K cap. Skip. |
| TRANSCOM26R005 | 493110 | Unknown | $50M | ❌ STALE + TOO LARGE | Pre-RFP from Jan 2026. Skip. |

**Finding: 0 actionable opportunities confirmed this scan cycle.**

---

## ROOT CAUSE

SAM.gov public API requires a registered, authenticated API key — the DEMO_KEY quota is exhausted or blocked. All third-party intelligence platforms (HigherGov, SamSearch, GovDash, GovTribe) gate their data behind paid subscriptions or authenticated accounts. Manual browser sessions cannot be replicated in this automated environment.

---

## UNBLOCK ACTION REQUIRED — PRESIDENT HUNTER

**Option A — Free SAM.gov API Key (Recommended)**
1. Go to: https://api.sam.gov/prod/users/register
2. Create account with your SAM.gov credentials
3. Request System Account with "Contract Opportunities" scope
4. Paste API key into CLAUDE.md under `SAM_API_KEY=`
5. This enables fully automated weekly scans — no GovTribe subscription needed

**Option B — Manual SAM.gov Search (Immediate workaround)**
1. Log in at sam.gov/opportunities
2. Filter: NAICS any of 484110, 493110, 541614, 488510, 492110
3. Filter: Set-Aside = SDVOSB
4. Filter: Posted Date = last 7 days
5. Filter: Status = Active
6. Sort by due date ascending
7. Paste the top 5–10 results into the chat — Claude will score and triage immediately

---

## NEXT SCAN

Scheduled: 2026-06-08 (Monday)
Prerequisites: SAM.gov API key registered OR manual search results provided by President Hunter

---

## BID CANDIDATES THIS CYCLE

None identified. No [DECISION NEEDED — PRESIDENT HUNTER] tags issued this cycle.

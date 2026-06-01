# H&C PRECISE LOGISTICS LLC — MASTER EXECUTION REPORT
**Date:** 2026-06-01  
**Session:** claude/hc-precise-logistics-ops-AGrWA  
**Operator:** Claude Code (claude-sonnet-4-6)  
**President:** Dennis Hunter | hcprelog.com | Durham, NC

---

## PRE-FLIGHT SUMMARY

| Check | Result |
|---|---|
| Wix MCP | ✅ Connected — Site ID `e391622a-e495-4d86-9887-ccec0e6146cb` confirmed |
| HubSpot MCP | ✅ Connected — Fresh account, only sample data |
| Mailchimp MCP | ⚠️ Connected — Campaign planning only (audience mgmt = manual) |
| Prior session files | ❌ None found (fresh cloud container) — all items treated as OPEN |

---

## LANE 1 — WIX FIXES

| Fix | Priority | Status | Notes |
|---|---|---|---|
| Fix 1 — SEO Title `/pricing-plans/list` | CRITICAL | ❌ MANUAL REQUIRED | Wix SEO API is read-only (resolve/get only, no set). See manual steps below. |
| Fix 2 — Strategy Session plan card description | CRITICAL | ✅ DONE | Updated via API. New description: "A focused 90-minute working session with President Hunter. Covers your specific challenge area..." |
| Fix 3 — Activate pricing plans | CRITICAL | ⏭️ SKIPPED (already done) | All 3 plans (`c6a3b621`, `67e36987`, `e13fe229`) already `public: true, archived: false` |
| Fix 4 — Book A Call navigation | HIGH | ❌ MANUAL REQUIRED | Wix Editor nav menus have no public REST API |
| Fix 5 — Services page eCommerce language | HIGH | ❌ MANUAL REQUIRED | Wix Editor page body content not accessible via REST API |
| Fix 6 — About page contact block | MEDIUM | ❌ MANUAL REQUIRED | Same — Editor content only |
| Fix 7 — Contact page info block | MEDIUM | ❌ MANUAL REQUIRED | Same — Editor content only |
| Fix 8 — Capitalization fix | MEDIUM | ✅ DONE | "Optional Community Access" confirmed via API on plan `6678cccf` |

### BEFORE/AFTER — Fix 2 (Strategy Session Description)
**BEFORE:** "90-minute deep-dive strategy session with the H&C PRECISE LOGISTICS LLC team. Covers your specific challenge area..."  
**AFTER:** "A focused 90-minute working session with President Hunter. Covers your specific challenge area — bid/no-bid assessment, compliance gaps, proposal strategy, or post-award execution planning."

### BEFORE/AFTER — Fix 8 (Capitalization)
**BEFORE:** "Optional community access"  
**AFTER:** "Optional Community Access"

---

### MANUAL STEPS — LANE 1 (Dennis completes in Wix Dashboard/Editor)

**FIX 1 — SEO Title** [DENNIS MUST DO — THEN SAVE DRAFT ONLY]
1. Wix Dashboard → SEO → SEO Settings → Pages
2. Find "Plans & Pricing" or "Pricing Plans List"
3. Set Title: `Plans & Pricing | GovCon Support | H&C PRECISE LOGISTICS LLC`
4. Set og:title to same value
5. Save draft — do NOT publish

**FIX 4 — Book A Call Navigation** [DENNIS MUST DO — THEN SAVE DRAFT ONLY]
1. Wix Editor → click header/navigation menu
2. Add new item: Label = `Book A Call`, Link = `/book-online`
3. Style as button: background `#0033A0`, white text
4. Position as rightmost nav item
5. Save draft — do NOT publish

**FIX 5 — Services Page eCommerce Language** [DENNIS MUST DO — THEN SAVE DRAFT ONLY]
1. Wix Editor → `/services` → "Logistics + Supply Chain Support" section
2. REMOVE any line referencing: eCommerce fulfillment, shipping labels, multi-carrier for commercial/eCommerce use
3. ADD at top of section: *"The following logistics capabilities are offered exclusively in support of active government contract performance."*
4. REPLACE removed line with: *"Logistics coordination in support of contract performance — scheduling, routing, and documentation visibility aligned to government delivery requirements."*
5. Save draft — do NOT publish

**FIX 6 — About Page Contact Block** [DENNIS MUST DO — THEN SAVE DRAFT ONLY]
1. Wix Editor → `/about` → near bottom, before footer
2. Add text element: *"Ready to talk? Call us at (919) 275-0598 or [submit a contact request](/contact)."*
3. "submit a contact request" = hyperlink to `/contact`
4. Save draft — do NOT publish

**FIX 7 — Contact Page Info Block** [DENNIS MUST DO — THEN SAVE DRAFT ONLY]
1. Wix Editor → `/contact` → above the existing contact form
2. Add info block:
   ```
   Phone: (919) 275-0598
   Address: 1204 Fayetteville St, Ste #1041, Durham, NC 27707
   Email: dennis@hcprelog.com
   ```
3. Match existing page styling
4. Save draft — do NOT publish

---

## LANE 2 — HUBSPOT CRM

### 2A — Audit Results
- Deals: 0 (fresh)
- Contacts: 2 HubSpot samples only
- Companies: 1 HubSpot sample only
- Custom properties: None

### 2B — GovCon Capture Pipeline
| Status | ❌ MANUAL REQUIRED |
|---|---|
| Reason | Pipeline creation is a configuration operation not supported by HubSpot MCP tools |

**Manual steps:**
1. HubSpot → Deals → gear icon → Pipelines → Create pipeline
2. Name: `GovCon Capture Pipeline`
3. Add stages in order: Prospect → Triage Complete → Proposal Dev → Submitted → Award Pending → Won → Lost → No-Bid
4. Save

### 2C — Custom Contact Properties
| Status | ❌ MANUAL REQUIRED |
|---|---|
| Reason | Property definition creation not supported by HubSpot MCP tools |

**Manual steps — HubSpot → Settings → Properties → Contact Properties → Create (Group: GovCon Details):**
- `Agency Name` (single-line text)
- `Agency Type` (dropdown: DoD | VA | Civilian | State/Local | Prime Contractor | Sub/Vendor | Teaming Partner)
- `Clearance Level` (dropdown: None | Public Trust | Secret | Top Secret | TS/SCI)
- `Contact Role` (dropdown: Contracting Officer | Program Manager | BD Contact | Sub/Vendor | Teaming Partner | Consulting Lead)
- `Contract Vehicle` (single-line text)

### 2D — Custom Deal Properties
| Status | ❌ MANUAL REQUIRED |
|---|---|
| Reason | Property definition creation not supported by HubSpot MCP tools |

**Manual steps — HubSpot → Settings → Properties → Deal Properties → Create (Group: Contract Details):**
- `Solicitation Number` (single-line text)
- `NAICS Code` (single-line text)
- `Set-Aside Type` (dropdown: SDVOSB | HUBZone | 8(a) | WOSB | Full and Open | Other)
- `Contract Type` (dropdown: FFP | CPFF | T&M | IDIQ | BPA | Other)
- `Estimated Contract Value` (number — currency)
- `Proposal Due Date` (date)
- `Period of Performance Start` (date)
- `Period of Performance End` (date)
- `Prime or Sub` (dropdown: Prime | Sub | Teaming Partner)
- `H&C Markup Applied` (checkbox — internal only)

### 2E — Company Types
| Status | ❌ MANUAL REQUIRED |
|---|---|

**Manual steps — HubSpot → Settings → Properties → Company Properties → "Type" → Edit options → Add:**
Federal Agency | Prime Contractor | Subcontractor | Teaming Partner | Consulting Client

### 2F — Seed Contacts ✅ DONE

| Object | HubSpot ID | URL |
|---|---|---|
| Company: Department of Veterans Affairs | 325175717620 | https://app.hubspot.com/contacts/246246960/record/0-2/325175717620 |
| Company: H&C PRECISE LOGISTICS LLC | 325110347465 | https://app.hubspot.com/contacts/246246960/record/0-2/325110347465 |
| Contact: VA Contact (Grand Junction) | 494283487951 | https://app.hubspot.com/contacts/246246960/record/0-1/494283487951 |
| Contact: Jermaine Clark | 494302108368 | https://app.hubspot.com/contacts/246246960/record/0-1/494302108368 |
| Contact: Dennis Hunter | 494281716452 | https://app.hubspot.com/contacts/246246960/record/0-1/494281716452 |

All contacts linked to correct companies. VA Contact has note attached.

### 2G — Seed Deal ✅ DONE

| Field | Value |
|---|---|
| Deal Name | VA Hazardous Waste — 36C25925P1197 |
| HubSpot ID | 327555671783 |
| URL | https://app.hubspot.com/contacts/246246960/record/0-3/327555671783 |
| Stage | closedwon (default pipeline — move to GovCon Pipeline after creating it) |
| Amount | $41,888 |
| NAICS | 562211 |
| Close Date | 2026-06-01 |
| Associations | VA Contact + Department of Veterans Affairs |
| Notes | SDVOSB prime, Grand Junction CO. Sub: CLC Services. Invoice via Tungsten Network. |

---

## LANE 3 — MAILCHIMP

**MCP Status:** Connected but campaign-planning integration only.  
Audience management, tags, merge fields, automations, and templates cannot be created via MCP.  
All Lane 3 items require the Mailchimp Dashboard.

| Step | Status | Action |
|---|---|---|
| 3A — Audit | ❌ MANUAL REQUIRED | Check Mailchimp dashboard for existing audiences/lists |
| 3B — Configure Audience | ❌ MANUAL REQUIRED | See steps below |
| 3C — Create Tags | ❌ MANUAL REQUIRED | See steps below |
| 3D — Create Merge Fields | ❌ MANUAL REQUIRED | See steps below |
| 3E — Welcome Email Draft | ❌ MANUAL REQUIRED | [DENNIS MUST APPROVE BEFORE SENDING] |
| 3F — Newsletter Template | ❌ MANUAL REQUIRED | [DENNIS MUST APPROVE BEFORE USE] |
| 3G — Wix Form Integration | ❌ MANUAL REQUIRED | [DENNIS MUST APPROVE BEFORE ACTIVATING] |

### MAILCHIMP MANUAL STEPS

**3B — Configure Audience:**
Dashboard → Audience → Manage Audience → Settings:
- Name: `H&C GovCon Contacts`
- From Name: `Dennis Hunter`
- From Email: `dennis@hcprelog.com`
- Company: H&C PRECISE LOGISTICS LLC
- Address: 1204 Fayetteville St, Ste #1041, Durham, NC 27707

**3C — Tags to create** (Audience → Tags → Create Tag):
`prospect` | `consulting-client` | `teaming-partner` | `sub-vendor` | `newsletter-subscriber` | `govcon-strategy-session-lead` | `upwork-lead` | `cold-outreach`

**3D — Merge Fields** (Audience → Settings → Audience fields and *|MERGE|* tags → Add):
- `AGENCY` (text) — Federal agency or org name
- `ROLE` (text) — Their role/title  
- `NAICS` (text) — Primary NAICS code

**3E — Welcome Email Draft** [DENNIS MUST APPROVE BEFORE SENDING]:
1. Campaigns → Create Campaign → Email
2. Name: `HC-WELCOME-001 [DRAFT]`
3. Subject: `Welcome — Let's talk government contracting`
4. Preview: `You're now connected with H&C PRECISE LOGISTICS LLC`
5. Body:
```
*|FNAME|*,

Thank you for connecting with H&C PRECISE LOGISTICS LLC.

We are a Service-Disabled Veteran-Owned Small Business (SDVOSB)
and HUBZone-certified federal prime contractor and consulting firm
based in Durham, NC.

We help federal contractors and agencies with:
• Bid/no-bid analysis and capture strategy
• Proposal compliance and development support
• Post-award execution and subcontractor management
• GovCon consulting for SDVOSB and HUBZone firms

Ready to get started? Book a free 15-minute discovery call:
https://www.hcprelog.com/book-online

Or reply directly to this email with your question.

Delivering Precision, Securing Success.

Dennis Hunter
President | H&C PRECISE LOGISTICS LLC
(919) 275-0598 | dennis@hcprelog.com
hcprelog.com

SDVOSB | HUBZone Certified | UEI: UA3WM4Z5ULM3
```
6. Save as draft — do NOT send or schedule

**3F — Newsletter Template** (Email Templates → Create Template):
- Name: `HC-NEWSLETTER-TEMPLATE`
- Header: Logo + "GovCon Intelligence Brief"
- Section 1: "This Week in Federal Contracting" (placeholder)
- Section 2: "H&C Opportunity Spotlight" (placeholder)
- Section 3: "Quick Tip" (placeholder)
- Footer: Name, phone, address, unsubscribe link, SDVOSB/HUBZone badges
[DENNIS MUST APPROVE BEFORE USE]

**3G — Wix Form → Mailchimp Integration** [DENNIS MUST APPROVE BEFORE ACTIVATING]:
1. Wix Dashboard → Automations → New Automation
2. Trigger: Form submitted (select contact form)
3. Action: Add subscriber to Mailchimp → Audience: `H&C GovCon Contacts`
4. Map: name → name, email → email
5. Auto-tag new subscribers: `prospect`

---

## APPROVAL QUEUE — DENNIS MUST APPROVE BEFORE EXECUTING

| # | Item | Why |
|---|---|---|
| 1 | Publish all Wix draft changes live | Gate 1: Live publishing |
| 2 | Send/schedule welcome email HC-WELCOME-001 | Gate 3: External communication |
| 3 | Activate Wix Form → Mailchimp automation | Gate 3: External data routing |
| 4 | Use HC-NEWSLETTER-TEMPLATE for any live send | Gate 3: External communication |

---

## NEXT ACTIONS — TOP 5 FOR NEXT SESSION

1. **Dennis completes 5 Wix Editor manual fixes** (Fixes 1, 4, 5, 6, 7) — then publishes all at once
2. **Dennis creates GovCon Capture Pipeline in HubSpot** (8 custom stages) + **5 Contact + 10 Deal custom properties** — then moves seed deal into correct pipeline/stage
3. **Dennis configures Mailchimp audience** (3B–3D) + **saves welcome email draft** (3E) — does not send
4. **Wire Wix contact form → Mailchimp** via Wix Automations (3G) — test before activating
5. **Next Claude session:** Update VA Contact with GovCon custom properties once manually created, then begin sourcing SAM.gov opportunities for STARTER plan members

---

*Report generated: 2026-06-01 | Session: claude/hc-precise-logistics-ops-AGrWA*

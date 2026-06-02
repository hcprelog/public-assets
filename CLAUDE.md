# CLAUDE.md — H&C PRECISE LOGISTICS LLC Business Operations Repo
Updated: June 2026 | Version: 2.2 | Pricing verified: hcprelog.com live

---

## COMPANY CONSTANTS
NAME:          H&C PRECISE LOGISTICS LLC      # Never abbreviate
PRESIDENT:     Dennis Akeem Jamaal Hunter      # Always "President Hunter"
DIRECTOR:      Jermaine Clark                  # "Director Clark" in vendor docs
DUNS:          117732260
CAGE:          95LL0
UEI:           UA3WM4Z5ULM3
EMAIL:         dennis@hcprelog.com
DIR_EMAIL:     directorclark@hcprelog.com
PHONE:         919-275-0598
ADDRESS:       1204 Fayetteville St Ste #1041, Durham, NC 27707
WEBSITE:       hcprelog.com
CERTS:         SDVOSB + HUBZone
BRAND_BLUE:    #0033A0
BRAND_GREEN:   #00B140
FONT:          Montserrat
NAICS_CORE:    484110, 484121, 484122, 492110, 492210, 493110, 488510, 541614, 541611, 561210
NAICS_ALL:     236220, 238210, 238220, 238990, 323111, 337910, 423840, 423850, 424120,
               484110, 484121, 484122, 484220, 484230, 488190, 488490, 488510, 488999,
               492110, 492210, 493110, 532420, 541519, 541611, 541613, 541614, 541990,
               561210, 561499, 561612, 561621, 561720, 561730
# H&C primes the contract — subs do the work. All codes are SAM.gov-verified.
VA_CONTRACT:   36C25925P1197  # Grand Junction CO — STABLE — LOW PRIORITY
MARKUP_MIN:    10%  # NEVER disclose externally
MARKUP_INT:    12%  # NEVER disclose externally

## LIVE PRICING (verified hcprelog.com/pricing-plans/list — June 2026)
# Subscriptions
PLAN_FREE:     GovCon Starter Academy (Free)   $0/unlimited
PLAN_START:    STARTER                          $97/month  | $930/year (save 20%)
PLAN_GROWTH:   GROWTH — MOST POPULAR           $297/month | $2,851/year (save 20%)
PLAN_PRIME:    PRIME READY                      $797/month | $7,651/year (save 20%)
# One-time services
SESSION_STRAT: GovCon Strategy Session (90 min) $347
SESSION_EBOOK: eBook: GovCon Starter Guide      $47
SESSION_SAM:   SAM.gov Registration Support     $197
SESSION_CAP:   Capability Statement Design      $297
# Internal
UPWORK_RATE:   $55/hr  # Not published on website

---

## APPROVAL GATES — HARD STOPS
NEVER execute without President Hunter's explicit written approval:
- [ ] Publishing anything live to Wix / hcprelog.com
- [ ] Submitting proposals, contracts, or RFP responses
- [ ] Any real-money transaction or purchase
- [ ] Creating credentials, API keys, or rotating secrets
- [ ] Mass outbound email campaigns
- [ ] Legal, insurance, or compliance attestations
- [ ] Lender representations or financing applications
⛔ NO hard credit pulls on Dennis Hunter under any circumstances.
⛔ NEVER disclose prime markup externally.

---

## API KEYS
# SAM.gov public API key — obtained 2026-06-02 by President Hunter
# Stored as GitHub Secret "SAM_API_KEY" in hcprelog/public-assets repo settings
# To retrieve: sam.gov → Account Details → enter password → copy key
SAM_API_KEY_SECRET_NAME: SAM_API_KEY

---

## CONNECTED MCP TOOLS
| Tool                   | Purpose                          | Priority |
|------------------------|----------------------------------|----------|
| Wix MCP                | hcprelog.com site management     | 1        |
| H&C Operations Make    | Workflow automation              | 2        |
| GitHub                 | Repo / code management           | 2        |
| QuickBooks MCP         | Financial data (read-only)       | 3        |
| Google Calendar MCP    | Scheduling                       | 4        |
| Gmail MCP              | Email operations                 | 4        |
| HubSpot MCP            | CRM + contact management         | 4        |
| Intuit Mailchimp MCP   | Email marketing                  | 5        |
| GovTribe MCP           | Federal opportunity intelligence | 5        |
| Google Drive MCP       | File storage                     | 5        |
| Apollo.io MCP          | Outreach/prospecting             | 6        |
| Docusign MCP           | Contract execution               | 6        |
| Tango MCP              | GovCon contract data             | 6        |

---

## REPO STRUCTURE
/ops
  /sops/              # HC-SOP-### numbered SOPs
  /templates/         # Reusable document templates
  /checklists/        # Operational checklists
  /briefs/            # Weekly KPI + executive summaries

/govcon
  /opportunities/     # [DATE]-[ID]-triage.md
  /proposals/         # Draft proposals + compliance matrices
  /vendors/           # Onboarding packets + preferred tracker + lost log
  /intelligence/      # Monthly market intelligence reports

/website
  /qa-logs/           # [DATE]-weekly-qa.md
  /content/           # Approved content queue
  /content/archive/   # Published content

/crm
  /upwork/            # Active lead file (one at a time)
  /consulting/        # Client intake + pipeline

/finance
  /forecasts/         # 30/60/90-day cash flow snapshots
  /invoices/          # VA contract + consulting invoice records

/education
  /umgc/              # DRAFT ONLY — never submit without approval

/automation
  /logs/              # Run logs
  /workflows/         # Make / MCP automation configs

/memory
  BUSINESS_STATE.md   # Current status, open items, priorities
  VENDOR_TRACKER.md   # Active + lost vendor log
  UPWORK_PIPELINE.md  # Active leads + status
  GOVCON_PIPELINE.md  # Opportunity pipeline
  PRICING_SHEET.md    # Live product pricing (sync from site quarterly)
  REPO_AUDIT.md       # Latest audit results

---

## SESSION START PROTOCOL
1. Read /memory/BUSINESS_STATE.md — load current priorities and open items
2. Check /govcon/opportunities/ — any pending triage items?
3. Check /crm/upwork/ — active lead status? (one at a time only)
4. Check for any [AWAITING APPROVAL] tags from last session
5. State active subagent role before beginning:
   wix-mcp-engineer | govcon-capture-analyst | proposal-compliance-qa
   vendor-sourcing-analyst | finance-ops-reviewer | research-verifier

---

## SESSION END PROTOCOL
1. Update /memory/BUSINESS_STATE.md:
   - Completed this session
   - Open items and blockers
   - Decisions made or needed
   - Next session top priorities
2. Log any automation changes in /automation/logs/
3. Tag pending decisions: [AWAITING PRESIDENT HUNTER APPROVAL]
4. Commit with format: [YYYY-MM-DD] [area] description — status

---

## WORK RULES
- Compliance-first. Audit-ready. No invented facts.
- govcon-opportunity-triage MUST run before any vendor contact
- Never contact vendors without packaged one-page Opportunity Summary
- Goods contracts: $5K–$25K · Net 30 · dropship preferred
- Yola Nights credit ($10K cap) = absolute last resort only
- Education files = DRAFT ONLY until explicitly approved to submit
- IFSM 441 Group 2: post Weeks 2 & 6; reply Weeks 1, 3, 4, 5, 7, 8
- VA contract 36C25925P1197 = stable — exclude from Claude Code priority prompts
- Upwork: one lead at a time — do not cross-reference active leads

---

## TOKEN-SAVING RULES
- Use read_file to load memory files — never ask President Hunter to paste
- Never regenerate an existing artifact — reference its file path
- Reference BUSINESS_STATE.md to re-establish context between sessions
- Suggest /compact when context exceeds ~50k tokens
- State subagent role once per session, not on every message
- If a fact is in memory files, cite the file — do not re-derive it
- Do not reproduce full SOPs in chat — reference file path and section number

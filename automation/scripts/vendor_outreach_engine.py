"""
H&C Precise Logistics — Vendor Outreach Automation Engine

Usage:
  python vendor_outreach_engine.py outreach          # find COLD/DRAFTED candidates → send emails
  python vendor_outreach_engine.py outreach --dry-run  # preview without sending
  python vendor_outreach_engine.py monitor           # check Gmail for replies → update tracker
  python vendor_outreach_engine.py both              # outreach then monitor

Requires env vars: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
"""

import re
import sys
from datetime import date
from pathlib import Path

import gmail_helper as gmail

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VENDORS_DIR = REPO_ROOT / "govcon" / "vendors"
LOG_FILE = REPO_ROOT / "automation" / "logs" / "VENDOR_OUTREACH_LOG.md"

# ── H&C constants ──────────────────────────────────────────────────────────────
HC_NAME = "Dennis Hunter"
HC_TITLE = "President, H&C Precise Logistics LLC"
HC_CERTS = "SDVOSB | HUBZone Certified"
HC_PHONE = "919-275-0598"
HC_EMAIL = "dennis@hcprelog.com"
HC_WEBSITE = "hcprelog.com"
HC_LOCATION = "Durham, NC"

SIGNATURE = f"""\
Best regards,
{HC_NAME}
{HC_TITLE}
{HC_CERTS} | {HC_LOCATION}
{HC_PHONE}
{HC_EMAIL}
{HC_WEBSITE}"""


# ── Data classes ───────────────────────────────────────────────────────────────

class Opportunity:
    __slots__ = ("sol_num", "location", "deadline")

    def __init__(self, sol_num: str, location: str, deadline: str):
        self.sol_num = sol_num
        self.location = location
        self.deadline = re.sub(r"[🔴🟠🟡]", "", deadline).strip()


class VendorCandidate:
    __slots__ = ("name", "email", "phone", "location", "tier", "status",
                 "notes", "naics", "file_path", "draft_id", "thread_id")

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


# ── Markdown helpers ───────────────────────────────────────────────────────────

def _get_field(block: str, field: str) -> str:
    m = re.search(rf"\|\s*{re.escape(field)}\s*\|\s*([^|]+)\s*\|", block)
    return re.sub(r"\*\*", "", m.group(1)).strip() if m else ""


def _extract_draft_id(status: str) -> str:
    m = re.search(r"Gmail draft ID:\s*(r[-\d]+)", status)
    return m.group(1) if m else ""


def _extract_thread_id(status: str) -> str:
    m = re.search(r"thread:\s*(\w+)", status)
    return m.group(1) if m else ""


def _parse_vendor_file(path: Path) -> tuple[list[Opportunity], list[VendorCandidate]]:
    content = path.read_text()
    naics = (re.search(r"naics-(\d+)", path.name) or type("", (), {"group": lambda *_: "000000"})()).group(1)

    # ── opportunities ──
    opps: list[Opportunity] = []
    opp_block = re.search(r"## ACTIVE OPPORTUNITIES.*?\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if opp_block:
        for row in re.finditer(
            r"\|\s*([^|]*36C\w+[^|]*)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*[^|]+\s*\|",
            opp_block.group(1),
        ):
            sol_match = re.search(r"36C\w+", row.group(1))
            if sol_match:
                opps.append(Opportunity(sol_match.group(), row.group(2).strip(), row.group(3)))

    # ── candidates ──
    candidates: list[VendorCandidate] = []
    for block in re.split(r"(?=^### )", content, flags=re.MULTILINE):
        if not block.startswith("### "):
            continue

        header = block.split("\n")[0]
        raw_name = re.sub(r"###\s*", "", header).strip()
        name = re.sub(r"\s*[⭐★✅⚠️🔴🟠🟡]+\s*.*$", "", raw_name).strip()
        name = re.split(r"\(Tier|\(tier|\*\(", name)[0].strip()

        status = _get_field(block, "Status")
        if not any(k in status for k in ("COLD", "EMAIL DRAFTED")):
            continue

        tier = 2 if "Tier 2" in block or "⚠️ Tier 2" in block else 1
        email = _get_field(block, "Email")
        if "No public" in email or "contact form" in email.lower():
            email = ""

        candidates.append(VendorCandidate(
            name=name,
            email=email,
            phone=_get_field(block, "Phone"),
            location=_get_field(block, "Location"),
            tier=tier,
            status=status,
            notes=_get_field(block, "Notes"),
            naics=naics,
            file_path=path,
            draft_id=_extract_draft_id(status),
            thread_id=_extract_thread_id(status),
        ))

    return opps, candidates


def _match_opportunity(candidate: VendorCandidate, opps: list[Opportunity]) -> Opportunity | None:
    """Match candidate to an opportunity by geographic state."""
    state_keywords = {
        "MA": ["Massachusetts", "Boston", "Bedford", "MA"],
        "VA": ["Virginia", "Norfolk", "Hampton", "VA"],
        "TN": ["Tennessee", "Kingsport", "Johnson City", "McDonald", "TN"],
    }
    loc = candidate.location
    for state, keywords in state_keywords.items():
        if any(k in loc for k in keywords):
            for opp in opps:
                if any(k in opp.location for k in keywords):
                    return opp
    return opps[0] if opps else None


def _update_status_in_file(path: Path, company_name: str, new_status: str) -> None:
    lines = path.read_text().split("\n")
    in_block = False
    result = []
    for line in lines:
        if re.match(r"^### ", line):
            in_block = company_name in line
        if in_block and re.match(r"\|\s*Status\s*\|", line):
            line = f"| Status | **{new_status}** |"
        result.append(line)
    path.write_text("\n".join(result))


def _log(entry: str) -> None:
    header = (
        "# VENDOR_OUTREACH_LOG.md — H&C PRECISE LOGISTICS LLC\n\n"
        "| Date | Company | Email | Action | Result | Thread ID |\n"
        "|---|---|---|---|---|---|\n"
    )
    if LOG_FILE.exists():
        content = LOG_FILE.read_text()
    else:
        content = header
    LOG_FILE.write_text(content.rstrip() + "\n" + entry + "\n")


# ── Email templates ─────────────────────────────────────────────────────────────

def _build_tier1_email(c: VendorCandidate, opp: Opportunity | None) -> tuple[str, str]:
    city = c.location.split(",")[0].strip() if c.location else "your area"
    sol_ref = f" (Solicitation {opp.sol_num})" if opp else ""
    deadline_line = (
        f"\n\nThe deadline on this opportunity is {opp.deadline} — I'd love to connect this week "
        "if you're open to it."
        if opp else ""
    )
    context = c.notes.split("—")[0].strip() if c.notes else (
        f"Your local expertise in {city} makes you an ideal execution partner for this work."
    )

    subject = f"VA Hospital Courier Contract — Partnership Opportunity in {city}"
    body = f"""\
Hi,

My name is Dennis Hunter, President of H&C Precise Logistics — we're an SDVOSB (Service-Disabled \
Veteran-Owned Small Business) and HUBZone certified federal contractor based in Durham, NC.

I'm reaching out because we've identified an active VA medical center contract for courier and \
delivery services in the {city} area{sol_ref}. It's a federal set-aside contract — reserved \
specifically for veteran-owned businesses like ours to prime.

Here's the opportunity in plain terms:

- H&C holds the prime contract and handles all compliance, billing, and government paperwork
- {c.name} runs the local routes — exactly what you're already doing for your current clients
- We pay you Net 30 once the government pays us — guaranteed federal money
- No government contracting experience required on your end{deadline_line}

{context}

I'd love 15 minutes to walk you through how the partnership works. Would you be available for a \
quick call this week?

{SIGNATURE}"""
    return subject, body


def _build_tier2_email(c: VendorCandidate, opp: Opportunity | None) -> tuple[str, str]:
    city = c.location.split(",")[0].strip() if c.location else "your area"
    sol_ref = f" ({opp.sol_num})" if opp else ""

    subject = f"SDVOSB Teaming Opportunity — Active VA Contract in {city}"
    body = f"""\
Hi,

My name is Dennis Hunter, President of H&C Precise Logistics — we're an SDVOSB and HUBZone \
certified federal contractor based in Durham, NC.

I'm reaching out because we have an active VA contract opportunity in the {city} area{sol_ref} \
set aside for SDVOSB-certified companies. I noticed you're already SAM-registered — that puts you \
ahead of most businesses in terms of government contracting readiness.

The challenge most SAM-registered companies face: without SDVOSB or HUBZone certifications, \
you're locked out of the set-aside market where the real opportunity is.

Here's what we're offering:

Option 1 — Immediate Revenue: We team with you as an execution sub on this contract. H&C primes, \
you run the local routes, we pay Net 30. Fast path to federal revenue while you build your own pipeline.

Option 2 — Long-Term Growth: Our PRIME READY plan ($797/mo) gives you SDVOSB teaming access on \
every bid we pursue, plus the complete roadmap to build your own set-aside pipeline.

I'd love a 15-minute call to walk through both options. Interested?

{SIGNATURE}"""
    return subject, body


# ── Reply classification ────────────────────────────────────────────────────────

_POSITIVE = {"yes", "interested", "sounds good", "let's talk", "let me know",
             "call", "schedule", "available", "great opportunity", "when can", "love to"}
_NEGATIVE = {"not interested", "no thank you", "no thanks", "pass", "not a fit",
             "do not contact", "unsubscribe", "remove me"}
_FOLLOWUP = {"question", "can you explain", "more information", "tell me more",
             "how does", "what is", "clarify"}


def _classify_reply(body: str) -> str:
    b = body.lower()
    if any(s in b for s in _NEGATIVE):
        return "NOT_INTERESTED"
    if any(s in b for s in _POSITIVE):
        return "INTERESTED"
    if any(s in b for s in _FOLLOWUP):
        return "FOLLOW_UP_NEEDED"
    return "REVIEW_NEEDED"


_STATUS_ICONS = {
    "INTERESTED": "🟢",
    "NOT_INTERESTED": "🔴",
    "FOLLOW_UP_NEEDED": "🟡",
    "REVIEW_NEEDED": "⚪",
}


# ── Main modes ─────────────────────────────────────────────────────────────────

def run_outreach(token: str, dry_run: bool = False) -> None:
    today = date.today().strftime("%Y-%m-%d")
    print(f"=== H&C Vendor Outreach — {'DRY RUN' if dry_run else 'LIVE'} ===\n")
    sent = skipped = 0

    for vendor_file in sorted(VENDORS_DIR.glob("naics-*.md")):
        print(f"File: {vendor_file.name}")
        opps, candidates = _parse_vendor_file(vendor_file)

        if not opps:
            print("  → No active opportunities linked — skipping\n")
            continue

        for c in candidates:
            if not c.email:
                print(f"  SKIP  {c.name}: no email (use phone/web form)")
                skipped += 1
                continue

            opp = _match_opportunity(c, opps)

            # ── Send existing draft ──
            if c.draft_id:
                print(f"  SEND DRAFT  {c.name} <{c.email}>  draft={c.draft_id}")
                if not dry_run:
                    try:
                        result = gmail.send_draft(c.draft_id, token)
                        tid = result.get("threadId", "unknown")
                        _update_status_in_file(vendor_file, c.name, f"EMAIL SENT {today} — thread: {tid}")
                        _log(f"| {today} | {c.name} | {c.email} | Draft sent | Awaiting reply | {tid} |")
                        print(f"         ✅ thread {tid}")
                        sent += 1
                    except Exception as exc:
                        print(f"         ❌ {exc}")
                else:
                    print(f"         [DRY RUN] would send draft {c.draft_id}")
                continue

            # ── Build + send new email ──
            if c.tier == 2:
                subject, body = _build_tier2_email(c, opp)
            else:
                subject, body = _build_tier1_email(c, opp)

            print(f"  SEND NEW    {c.name} <{c.email}>  Tier {c.tier}  opp={opp.sol_num if opp else 'none'}")
            if not dry_run:
                try:
                    result = gmail.send_email(c.email, subject, body, token)
                    tid = result.get("threadId", "unknown")
                    _update_status_in_file(vendor_file, c.name, f"EMAIL SENT {today} — thread: {tid}")
                    _log(f"| {today} | {c.name} | {c.email} | Email sent | Awaiting reply | {tid} |")
                    print(f"         ✅ thread {tid}")
                    sent += 1
                except Exception as exc:
                    print(f"         ❌ {exc}")
            else:
                print(f"         [DRY RUN] Subject: {subject[:60]}...")

        print()

    print(f"=== DONE: {sent} sent, {skipped} skipped (no email) ===")


def run_monitor(token: str) -> None:
    today = date.today().strftime("%Y-%m-%d")
    print("=== H&C Vendor Reply Monitor ===\n")
    replies_found = 0

    for vendor_file in sorted(VENDORS_DIR.glob("naics-*.md")):
        content = vendor_file.read_text()

        # Find all blocks where an email was sent and we have a thread ID
        for block_match in re.finditer(
            r"### ([^\n]+)\n(?:(?!^### )[\s\S])*?Status.*?EMAIL SENT.*?thread:\s*(\w+)",
            content,
            re.MULTILINE,
        ):
            raw_name = re.sub(r"###\s*|[⭐★✅⚠️🔴🟠🟡]+", "", block_match.group(1)).strip()
            thread_id = block_match.group(2).strip()

            messages = gmail.get_thread_messages(thread_id, token)

            if len(messages) <= 1:
                print(f"  {raw_name}: no reply yet")
                continue

            # At least one reply exists — read the latest message
            latest_id = messages[-1]["id"]
            body = gmail.get_message_plaintext(latest_id, token)
            classification = _classify_reply(body)
            icon = _STATUS_ICONS[classification]
            new_status = f"REPLIED {today} {icon} {classification.replace('_', ' ')} — check inbox"

            _update_status_in_file(vendor_file, raw_name, new_status)
            _log(f"| {today} | {raw_name} | — | Reply received | {classification} | {thread_id} |")
            print(f"  {raw_name}: 📬 {classification}")
            replies_found += 1

    print(f"\n=== MONITOR DONE: {replies_found} replies found ===")


# ── Entry point ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "outreach"
    dry_run = "--dry-run" in sys.argv

    token = gmail.get_access_token()

    if mode == "outreach":
        run_outreach(token, dry_run)
    elif mode == "monitor":
        run_monitor(token)
    elif mode == "both":
        run_outreach(token, dry_run)
        run_monitor(token)
    else:
        print(f"Unknown mode '{mode}'. Use: outreach | monitor | both")
        sys.exit(1)

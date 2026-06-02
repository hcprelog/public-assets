import imaplib
import email
import os
import re
from datetime import date
from email.header import decode_header
from pathlib import Path

GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VENDORS_DIR = REPO_ROOT / "govcon" / "vendors"
LOG_FILE = REPO_ROOT / "automation" / "logs" / "VENDOR_OUTREACH_LOG.md"

VENDOR_MAP = {
    "eccconline@gmail.com": "East Coast Courier (ECCC)",
    "info@courierva.com": "CourierVA (Bruce)",
    "dispatch@tricitylogistics.com": "Tri City Logistics",
    "info@allstatecouriers.com": "Allstate Courier Systems",
}

POSITIVE = ["yes", "interested", "sounds good", "let's talk", "available",
             "call", "schedule", "when can", "love to", "definitely"]
NEGATIVE = ["not interested", "no thank", "pass", "not a fit",
             "do not contact", "unsubscribe", "remove"]
FOLLOWUP = ["question", "more info", "can you explain", "tell me more",
             "how does", "what is", "clarify"]


def classify(body):
    b = body.lower()
    if any(s in b for s in NEGATIVE):
        return "NOT_INTERESTED", "🔴"
    if any(s in b for s in POSITIVE):
        return "INTERESTED", "🟢"
    if any(s in b for s in FOLLOWUP):
        return "FOLLOW_UP_NEEDED", "🟡"
    return "REVIEW_NEEDED", "⚪"


def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return part.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode("utf-8", errors="replace")
        except Exception:
            pass
    return ""


def update_vendor_status(company_name, new_status):
    for vendor_file in VENDORS_DIR.glob("naics-*.md"):
        content = vendor_file.read_text()
        if company_name not in content:
            continue
        lines = content.split("\n")
        in_block = False
        result = []
        for line in lines:
            if re.match(r"^### ", line):
                in_block = company_name in line
            if in_block and re.match(r"\|\s*Status\s*\|", line):
                line = f"| Status | **{new_status}** |"
            result.append(line)
        vendor_file.write_text("\n".join(result))
        print(f"  Updated {vendor_file.name}")
        return


def append_log(entry):
    header = (
        "# VENDOR_OUTREACH_LOG.md — H&C PRECISE LOGISTICS LLC\n\n"
        "| Date | Company | Email | Action | Result | Thread ID |\n"
        "|---|---|---|---|---|---|\n"
    )
    content = LOG_FILE.read_text() if LOG_FILE.exists() else header
    LOG_FILE.write_text(content.rstrip() + "\n" + entry + "\n")


def main():
    today = date.today().strftime("%Y-%m-%d")
    print("=== H&C Vendor Reply Monitor ===")

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
    mail.select("inbox")

    replies_found = 0

    for vendor_email, company_name in VENDOR_MAP.items():
        print(f"\nChecking replies from {company_name} <{vendor_email}>...")
        status, data = mail.search(None, f'FROM "{vendor_email}"')
        if status != "OK" or not data[0]:
            print("  No reply found")
            continue

        msg_ids = data[0].split()
        print(f"  {len(msg_ids)} message(s) found")

        for msg_id in msg_ids:
            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode("utf-8", errors="replace")
            body = get_body(msg)
            classification, icon = classify(body)
            new_status = f"REPLIED {today} {icon} {classification.replace('_', ' ')} — check inbox"

            print(f"  Subject: {subject}")
            print(f"  Classification: {classification}")

            update_vendor_status(company_name, new_status)
            append_log(
                f"| {today} | {company_name} | {vendor_email} "
                f"| Reply received | {classification} | — |"
            )
            replies_found += 1

    mail.close()
    mail.logout()
    print(f"\n=== DONE: {replies_found} replies found ===")


if __name__ == "__main__":
    main()

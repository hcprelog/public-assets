"""
H&C PRECISE LOGISTICS LLC - Auto-Poster Failure Alert

Runs only when the "Post to Instagram and Facebook" step in instagram-post.yml
fails. Sends a same-day email so a bad run is never discovered a week later --
the Jul 27-31 2026 outage (runs #47-#51) was only found by manual inspection
five days after it started, because nothing was watching for the failure.

Skips cleanly (does not raise) if GMAIL_USER / GMAIL_APP_PASSWORD are not
configured, so a missing secret here can never break the workflow itself.
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from datetime import datetime, timezone

GMAIL_USER = os.environ.get("GMAIL_USER", "").strip()
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
ALERT_TO = os.environ.get("ALERT_TO", GMAIL_USER).strip()
RUN_URL = os.environ.get("RUN_URL", "")
WORKFLOW_NAME = os.environ.get("WORKFLOW_NAME", "Instagram Daily Post")


def main():
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("[Alert] Skipped -- GMAIL_USER / GMAIL_APP_PASSWORD not configured.")
        return

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    subject = f"[ALERT] {WORKFLOW_NAME} failed -- {now}"
    body = (
        f"The {WORKFLOW_NAME} automation failed and did NOT post today.\n\n"
        f"Run log: {RUN_URL}\n\n"
        f"Open the run log above and check the last lines of the "
        f"'Post to Instagram and Facebook' step for the exact error.\n\n"
        f"This alert exists so a failure is caught the same day instead of "
        f"going unnoticed for days, as happened Jul 27-31 2026."
    )

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = ALERT_TO

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls(context=context)
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, [ALERT_TO], msg.as_string())
        print(f"[Alert] Failure email sent to {ALERT_TO}")
    except Exception as e:
        print(f"[Alert] Could not send failure email: {e}")


if __name__ == "__main__":
    main()

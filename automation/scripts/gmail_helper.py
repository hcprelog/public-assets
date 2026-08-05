"""
Gmail API helper for H&C Precise Logistics vendor outreach automation.

Required GitHub Secrets:
  GMAIL_CLIENT_ID      — from Google Cloud Console OAuth 2.0 client
  GMAIL_CLIENT_SECRET  — from Google Cloud Console OAuth 2.0 client
  GMAIL_REFRESH_TOKEN  — generated via OAuth consent flow (see SETUP.md)

Setup guide: /automation/scripts/GMAIL_SETUP.md
"""

import base64
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

_TOKEN_URL = "https://oauth2.googleapis.com/token"
_API = "https://gmail.googleapis.com/gmail/v1/users/me"


def get_access_token() -> str:
    resp = requests.post(_TOKEN_URL, data={
        "client_id": os.environ["GMAIL_CLIENT_ID"],
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
        "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def send_email(to: str, subject: str, body: str, token: str) -> dict:
    """Send a plain-text email from dennis@hcprelog.com. Returns message dict with threadId."""
    msg = MIMEMultipart("alternative")
    msg["To"] = to
    msg["From"] = "H&C Precise Logistics <dennis@hcprelog.com>"
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    resp = requests.post(
        f"{_API}/messages/send",
        headers=_auth_headers(token),
        json={"raw": raw},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def send_draft(draft_id: str, token: str) -> dict:
    """Send an existing Gmail draft by its ID. Returns message dict with threadId."""
    resp = requests.post(
        f"{_API}/drafts/send",
        headers=_auth_headers(token),
        json={"id": draft_id},
        timeout=30,
    )
    if resp.status_code == 404:
        raise ValueError(f"Draft {draft_id} not found — may already have been sent manually")
    resp.raise_for_status()
    return resp.json()


def get_thread_messages(thread_id: str, token: str) -> list[dict]:
    """Return all messages in a thread. Empty list if thread not found."""
    resp = requests.get(
        f"{_API}/threads/{thread_id}",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
        timeout=15,
    )
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json().get("messages", [])


def get_message_plaintext(message_id: str, token: str) -> str:
    """Return the plain-text body of a message."""
    resp = requests.get(
        f"{_API}/messages/{message_id}",
        headers={"Authorization": f"Bearer {token}"},
        params={"format": "full"},
        timeout=15,
    )
    resp.raise_for_status()

    payload = resp.json().get("payload", {})
    parts = payload.get("parts") or [payload]

    for part in parts:
        if part.get("mimeType") == "text/plain":
            data = part.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""


def search_messages(query: str, token: str, max_results: int = 50) -> list[dict]:
    """Return a list of message stubs matching a Gmail search query."""
    resp = requests.get(
        f"{_API}/messages",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": query, "maxResults": max_results},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("messages", [])

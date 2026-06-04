"""
H&C PRECISE LOGISTICS LLC - Instagram Token Auto-Refresh
Runs every 45 days via refresh-instagram-token.yml
Refreshes the long-lived Instagram access token (60-day tokens)
and updates the INSTAGRAM_ACCESS_TOKEN GitHub Secret automatically.
"""

import os
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime, timezone

INSTAGRAM_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
INSTAGRAM_APP_ID       = os.environ["INSTAGRAM_APP_ID"]
INSTAGRAM_APP_SECRET   = os.environ["INSTAGRAM_APP_SECRET"]
GITHUB_TOKEN           = os.environ["GITHUB_TOKEN"]
GITHUB_REPO            = os.environ.get("GITHUB_REPOSITORY", "hcprelog/public-assets")

def http(method, url, headers=None, data=None, timeout=30):
    headers = headers or {}
    if isinstance(data, dict):
        data = json.dumps(data).encode()
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode()
            return r.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, {"error": body}

def refresh_token():
    """Exchange current token for a fresh 60-day token."""
    print("Refreshing Instagram access token...")
    url = (
        "https://graph.instagram.com/refresh_access_token"
        "?grant_type=ig_refresh_token"
        f"&access_token={INSTAGRAM_ACCESS_TOKEN}"
    )
    status, resp = http("GET", url)
    if status == 200 and "access_token" in resp:
        new_token = resp["access_token"]
        expires_in = resp.get("expires_in", 5183944)
        print(f"New token obtained. Expires in {expires_in // 86400} days.")
        return new_token
    print(f"Refresh failed {status}: {resp}")
    return None

def get_repo_public_key():
    """Get the repo encryption public key for GitHub Secrets."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/public-key"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    status, resp = http("GET", url, headers=headers)
    if status == 200:
        return resp["key_id"], resp["key"]
    print(f"Could not get repo public key: {status}")
    return None, None

def encrypt_secret(public_key_b64, secret_value):
    """Encrypt a secret using the repo public key (libsodium sealed box)."""
    try:
        from nacl import encoding, public
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "pynacl"], capture_output=True)
        from nacl import encoding, public
    pk = public.PublicKey(public_key_b64.encode(), encoding.Base64Encoder())
    box = public.SealedBox(pk)
    encrypted = box.encrypt(secret_value.encode())
    return base64.b64encode(encrypted).decode()

def update_github_secret(name, value, key_id, public_key):
    """Update a GitHub Actions secret."""
    encrypted = encrypt_secret(public_key, value)
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/{name}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    body = {"encrypted_value": encrypted, "key_id": key_id}
    status, _ = http("PUT", url, headers=headers, data=body)
    return status in (201, 204)

def main():
    print("=" * 60)
    print("H&C PRECISE LOGISTICS LLC - Token Refresh")
    print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    new_token = refresh_token()
    if not new_token:
        print("FATAL: could not refresh token")
        raise SystemExit(1)

    key_id, public_key = get_repo_public_key()
    if not key_id:
        print("FATAL: could not get repo encryption key")
        raise SystemExit(1)

    ok = update_github_secret("INSTAGRAM_ACCESS_TOKEN", new_token, key_id, public_key)
    if ok:
        print("INSTAGRAM_ACCESS_TOKEN secret updated")
        print("Token will be valid for another 60 days.")
    else:
        print("FATAL: could not update GitHub Secret")
        raise SystemExit(1)

if __name__ == "__main__":
    main()

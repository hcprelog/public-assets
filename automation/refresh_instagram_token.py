import os
import json
import base64
import urllib.request
import urllib.parse

APP_ID       = os.environ["INSTAGRAM_APP_ID"]
APP_SECRET   = os.environ["INSTAGRAM_APP_SECRET"]
CURRENT_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
GITHUB_TOKEN  = os.environ["GITHUB_TOKEN"]
GITHUB_REPO   = "hcprelog/public-assets"

print("Refreshing Instagram long-lived access token...")

# Step 1: Refresh the token
url = (f"https://graph.facebook.com/v25.0/oauth/access_token"
       f"?grant_type=ig_refresh_token"
       f"&access_token={CURRENT_TOKEN}")

req = urllib.request.Request(url)
with urllib.request.urlopen(req) as r:
    data = json.loads(r.read())

if "access_token" not in data:
    raise Exception(f"Token refresh failed: {data}")

new_token = data["access_token"]
expires_in = data.get("expires_in", 5184000)
print(f"New token obtained. Expires in: {expires_in} seconds (~{expires_in//86400} days)")

# Step 2: Get GitHub repo public key for encryption
key_req = urllib.request.Request(
    f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/public-key",
    headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
)
with urllib.request.urlopen(key_req) as r:
    key_data = json.loads(r.read())

key_id = key_data["key_id"]
public_key_b64 = key_data["key"]

# Step 3: Encrypt and save new token to GitHub Secrets
from nacl import encoding, public as nacl_public

def encrypt(pub_key_b64, value):
    pk = nacl_public.PublicKey(pub_key_b64.encode(), encoding.Base64Encoder())
    box = nacl_public.SealedBox(pk)
    return base64.b64encode(box.encrypt(value.encode())).decode()

encrypted = encrypt(public_key_b64, new_token)
payload = json.dumps({"encrypted_value": encrypted, "key_id": key_id}).encode()

secret_req = urllib.request.Request(
    f"https://api.github.com/repos/{GITHUB_REPO}/actions/secrets/INSTAGRAM_ACCESS_TOKEN",
    data=payload, method="PUT",
    headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }
)
with urllib.request.urlopen(secret_req) as r:
    print(f"✅ INSTAGRAM_ACCESS_TOKEN updated in GitHub Secrets: HTTP {r.status}")

print(f"Token refresh complete. Next refresh due in ~{expires_in//86400} days.")

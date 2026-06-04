"""
H&C PRECISE LOGISTICS LLC — One-time Avatar Upload Script
Run this ONCE locally (after installing Python + requests) to upload the
two brand avatar images to GitHub Pages so create_reel.py can use them.

Usage:
  pip install requests
  python upload_avatars.py
"""

import os
import json
import base64
import urllib.request

GITHUB_TOKEN = input("Paste your GitHub PAT (needs repo scope): ").strip()
GITHUB_REPO  = "hcprelog/public-assets"

AVATARS = {
    "avatars/marcus-hale.jpg":   input("Full path to Marcus Hale image (male headshot): ").strip(),
    "avatars/arielle-grant.jpg": input("Full path to Arielle Grant image (female headshot): ").strip(),
}

def upload(repo_path, local_path):
    with open(local_path, "rb") as f:
        raw = f.read()
    encoded = base64.b64encode(raw).decode()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    # Check if file exists for sha
    req = urllib.request.Request(url, headers=headers, method="GET")
    sha = None
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            existing = json.loads(r.read().decode())
            sha = existing.get("sha")
    except Exception:
        pass

    body = {"message": f"upload avatar: {repo_path}", "content": encoded}
    if sha:
        body["sha"] = sha
    body_bytes = json.dumps(body).encode()
    put_req = urllib.request.Request(url, data=body_bytes, headers={**headers, "Content-Type": "application/json"}, method="PUT")
    try:
        with urllib.request.urlopen(put_req, timeout=30) as r:
            status = r.status
    except urllib.error.HTTPError as e:
        status = e.code

    if status in (200, 201):
        pages_url = f"https://hcprelog.github.io/public-assets/{repo_path}"
        print(f"  Uploaded {repo_path}")
        print(f"  Public URL: {pages_url}")
    else:
        print(f"  FAILED {repo_path}: HTTP {status}")

print("\nUploading avatars to GitHub Pages...")
for repo_path, local_path in AVATARS.items():
    if os.path.exists(local_path):
        upload(repo_path, local_path)
    else:
        print(f"  File not found: {local_path}")

print("\nDone. Update AVATAR_IMAGES dict in create_reel.py if URLs differ.")
print("GitHub Pages URL format: https://hcprelog.github.io/public-assets/avatars/marcus-hale.jpg")

"""
H&C PRECISE LOGISTICS LLC — Instagram Reels Creator (D-ID Talking Avatar)
Runs weekly (Wednesdays 10AM ET) via instagram-reel.yml

Pipeline:
1. Pick a weekly Reel topic (Marcus or Arielle)
2. Generate 30-45 second talking script via Claude
3. Send avatar image + script to D-ID API → talking head MP4
4. Upload video to GitHub Pages for public URL
5. Post as Instagram Reel via Graph API

D-ID Lite plan: $5.99/month = 10 min of video
At 1 video/week (45s) = ~3 min/month — well within Lite tier
Free trial: 20 credits (~5 min) covers initial testing
Sign up + API key: https://studio.d-id.com
"""

import os
import json
import base64
import time
import sys
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ── Secrets ───────────────────────────────────────────────────────────────────
INSTAGRAM_USER_ID      = os.environ["INSTAGRAM_USER_ID"]
INSTAGRAM_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
ANTHROPIC_API_KEY      = os.environ.get("ANTHROPIC_API_KEY", "")
D_ID_API_KEY           = os.environ["D_ID_API_KEY"]
GITHUB_TOKEN           = os.environ["GITHUB_TOKEN"]
GITHUB_REPO            = os.environ.get("GITHUB_REPOSITORY", "hcprelog/public-assets")

IG_API_BASE  = "https://graph.facebook.com/v25.0"
D_ID_API_BASE = "https://api.d-id.com"

# ── Brand avatars (GitHub Pages) ──────────────────────────────────────────────
AVATAR_IMAGES = {
    "marcus":  "https://hcprelog.github.io/public-assets/avatars/Marcus%20Hale.png",
    "arielle": "https://hcprelog.github.io/public-assets/avatars/Arielle%20Grant.png",
}

# Microsoft Neural TTS voices via D-ID
AVATAR_VOICES = {
    "marcus":  {"type": "microsoft", "voice_id": "en-US-DavisNeural"},
    "arielle": {"type": "microsoft", "voice_id": "en-US-JennyNeural"},
}

# ── Weekly Reel topics ────────────────────────────────────────────────────────
REEL_TOPICS = [
    {"id": "r-bid-no-bid",     "avatar": "marcus",  "title": "3 Questions to Ask Before Bidding on Any Contract"},
    {"id": "r-sam-steps",      "avatar": "arielle", "title": "SAM.gov Registration in 5 Steps"},
    {"id": "r-sdvosb-power",   "avatar": "marcus",  "title": "Why SDVOSB Opens Doors Other Certifications Don't"},
    {"id": "r-first-contract", "avatar": "arielle", "title": "How to Get Your First Government Contract"},
    {"id": "r-cash-flow",      "avatar": "marcus",  "title": "GovCon Cash Flow: What Nobody Tells You"},
    {"id": "r-capability",     "avatar": "arielle", "title": "Your Capability Statement Checklist"},
    {"id": "r-compliance",     "avatar": "marcus",  "title": "What a Compliance Matrix Actually Does"},
    {"id": "r-teaming",        "avatar": "marcus",  "title": "How to Team Your Way Into Bigger Contracts"},
    {"id": "r-hubzone",        "avatar": "arielle", "title": "HubZone: Are You Missing This Certification?"},
    {"id": "r-post-award",     "avatar": "marcus",  "title": "Post-Award Pitfalls That Kill Small Businesses"},
]

AVATAR_PERSONAS = {
    "marcus": (
        "You are Marcus Hale, GovCon Operations Advisor for H&C PRECISE LOGISTICS LLC. "
        "Direct, credible, experienced federal contractor. No fluff. Practical insights only."
    ),
    "arielle": (
        "You are Arielle Grant, Business Growth Advisor for H&C PRECISE LOGISTICS LLC. "
        "Warm, encouraging, practical. You guide businesses through their first steps in GovCon."
    ),
}

# ── HTTP helper ───────────────────────────────────────────────────────────────
def http(method, url, headers=None, data=None, timeout=60):
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

def d_id_headers():
    """D-ID Basic auth: base64(api_key:)"""
    encoded = base64.b64encode(f"{D_ID_API_KEY}:".encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — SCRIPT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def generate_script(topic):
    """
    Generate a 30-45 second speaking script (~75-100 words).
    Structured as: hook → 2-3 insights → CTA
    """
    if not ANTHROPIC_API_KEY:
        return fallback_script(topic)

    persona = AVATAR_PERSONAS.get(topic["avatar"], AVATAR_PERSONAS["arielle"])
    system = (
        f"{persona} "
        f"Company: H&C PRECISE LOGISTICS LLC. Website: hcprelog.com. "
        f"RULE: Always say 'H&C PRECISE LOGISTICS LLC' — exact name. "
        f"Speak naturally as if on camera. No stage directions. No asterisks. "
        f"Pure spoken words only."
    )
    user = (
        f"Write a 30-45 second video script (80-100 words) for an Instagram Reel.\n"
        f"Topic: {topic['title']}\n\n"
        f"Structure:\n"
        f"1. Open with a strong hook (1 sentence)\n"
        f"2. Deliver 2-3 sharp, practical insights (no filler)\n"
        f"3. End with a clear CTA mentioning hcprelog.com\n\n"
        f"Write ONLY the spoken words. No labels. No directions. Natural speech rhythm.\n"
        f"Stay under 100 words."
    )
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-opus-4-5",
        "max_tokens": 300,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    status, resp = http("POST", "https://api.anthropic.com/v1/messages", headers=headers, data=body, timeout=30)
    if status == 200:
        script = resp["content"][0]["text"].strip()
        word_count = len(script.split())
        print(f"[Script] Generated: {word_count} words (~{word_count//2}s speaking time)")
        return script
    print(f"[Script] Claude error {status}: {resp}")
    return fallback_script(topic)

def fallback_script(topic):
    return (
        f"If you're serious about government contracting, here's what most people miss about {topic['title'].lower()}. "
        f"At H&C PRECISE LOGISTICS LLC, we help businesses navigate every step — "
        f"from registration to your first awarded contract. "
        f"SDVOSB and HubZone certified. Based in Durham, North Carolina. "
        f"Start at hcprelog.com — the free GovCon Starter Academy is waiting for you."
    )

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — D-ID TALKING AVATAR VIDEO
# ═══════════════════════════════════════════════════════════════════════════════

def create_did_talk(avatar_url, script, avatar_key):
    """
    Submit a talking video request to D-ID API.
    Returns the talk ID for polling.
    """
    print(f"\n[D-ID] Creating talk for avatar: {avatar_key}")
    print(f"[D-ID] Script preview: {script[:80]}...")

    voice = AVATAR_VOICES.get(avatar_key, AVATAR_VOICES["arielle"])

    body = {
        "source_url": avatar_url,
        "script": {
            "type": "text",
            "input": script,
            "provider": {
                "type": voice["type"],
                "voice_id": voice["voice_id"],
            },
        },
        "config": {
            "fluent": True,
            "pad_audio": 0.0,
            "stitch": True,
        },
    }

    status, resp = http("POST", f"{D_ID_API_BASE}/talks", headers=d_id_headers(), data=body, timeout=30)

    if status in (200, 201) and "id" in resp:
        talk_id = resp["id"]
        print(f"[D-ID] Talk created: {talk_id}")
        return talk_id

    print(f"[D-ID] Creation error {status}: {resp}")

    # Diagnose common errors
    error_msg = str(resp)
    if "credits" in error_msg.lower() or "limit" in error_msg.lower():
        print("[D-ID] Out of credits. Add credits at: https://studio.d-id.com/settings")
    elif status == 401:
        print("[D-ID] Auth failed. Check D_ID_API_KEY secret.")
    elif "face" in error_msg.lower():
        print("[D-ID] Could not detect face in avatar image. Check avatar URL is accessible.")

    return None

def poll_did_talk(talk_id, max_wait=180):
    """
    Poll D-ID until video is ready or timeout.
    D-ID typically takes 30-90 seconds for a 45-second video.
    Returns the result_url or None.
    """
    print(f"[D-ID] Waiting for video to render (up to {max_wait}s)...")
    start = time.time()
    attempt = 0

    while time.time() - start < max_wait:
        time.sleep(8)
        attempt += 1
        status, resp = http("GET", f"{D_ID_API_BASE}/talks/{talk_id}", headers=d_id_headers(), timeout=15)

        if status != 200:
            print(f"[D-ID] Poll error {status}: {resp}")
            continue

        talk_status = resp.get("status", "")
        print(f"[D-ID] Status [{attempt}]: {talk_status}")

        if talk_status == "done":
            result_url = resp.get("result_url")
            if result_url:
                print(f"[D-ID] Video ready: {result_url[:60]}...")
                return result_url
            print("[D-ID] Done but no result_url in response")
            return None

        if talk_status == "error":
            error = resp.get("error", {})
            print(f"[D-ID] Render error: {error}")
            return None

    print(f"[D-ID] Timeout after {max_wait}s")
    return None

def download_video(video_url, tmp_path):
    """Download the D-ID video to a temp file."""
    print(f"[Video] Downloading from D-ID...")
    try:
        urllib.request.urlretrieve(video_url, tmp_path)
        import os as _os
        size = _os.path.getsize(tmp_path)
        print(f"[Video] Downloaded: {size:,} bytes ({size/1024/1024:.1f} MB)")
        return True
    except Exception as e:
        print(f"[Video] Download failed: {e}")
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — UPLOAD TO GITHUB PAGES
# ═══════════════════════════════════════════════════════════════════════════════

def upload_to_pages(local_path, repo_path):
    """Upload MP4 to GitHub repo → served via GitHub Pages as public URL."""
    with open(local_path, "rb") as f:
        raw = f.read()
    encoded  = base64.b64encode(raw).decode()
    gh_url   = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    headers  = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    # Check for existing file sha
    status, existing = http("GET", gh_url, headers=headers, timeout=15)
    sha = existing.get("sha") if status == 200 else None

    body = {"message": f"auto: reel {repo_path}", "content": encoded}
    if sha:
        body["sha"] = sha

    print(f"[Upload] Uploading video to GitHub Pages ({len(raw)/1024/1024:.1f} MB)...")
    status, resp = http("PUT", gh_url, headers=headers, data=body, timeout=120)

    if status in (200, 201):
        public_url = f"https://hcprelog.github.io/public-assets/{repo_path}"
        print(f"[Upload] Live at: {public_url}")
        return public_url

    print(f"[Upload] Failed {status}: {resp}")
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — INSTAGRAM REEL POST
# ═══════════════════════════════════════════════════════════════════════════════

def generate_reel_caption(topic, avatar_key):
    """Short Instagram caption for the Reel."""
    if not ANTHROPIC_API_KEY:
        return f"Watch to the end.\n\nH&C PRECISE LOGISTICS LLC — GovCon execution support.\nSDVOSB + HubZone certified.\nhcprelog.com\n\n#GovCon #SDVOSB #HubZone #FederalContracting #SmallBusiness #VeteranOwned #HCPreciseLogistics"

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-opus-4-5",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": (
            f"Write a short Instagram Reel caption (max 50 words + 10 hashtags) for H&C PRECISE LOGISTICS LLC.\n"
            f"Topic: {topic['title']}\n"
            f"End with: hcprelog.com\n"
            f"Keep it punchy. Start with 'Watch to the end.' or a similar hook."
        )}]
    }
    status, resp = http("POST", "https://api.anthropic.com/v1/messages", headers=headers, data=body, timeout=20)
    if status == 200:
        return resp["content"][0]["text"].strip()
    return f"Watch to the end.\n\nhcprelog.com\n\n#GovCon #SDVOSB #HubZone #FederalContracting #HCPreciseLogistics"

def ig_post_reel(video_url, caption):
    """Post video as Instagram Reel via Graph API."""
    print(f"\n[Instagram] Creating Reel container...")

    params = urllib.parse.urlencode({
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    })
    status, resp = http(
        "POST",
        f"{IG_API_BASE}/{INSTAGRAM_USER_ID}/media",
        data=params.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )

    if status != 200 or "id" not in resp:
        print(f"[Instagram] Container error {status}: {resp}")
        return False

    container_id = resp["id"]
    print(f"[Instagram] Container: {container_id} — processing...")

    # Poll until video is processed by Instagram (up to 4 min)
    for attempt in range(30):
        time.sleep(8)
        check_url = f"{IG_API_BASE}/{container_id}?fields=status_code,status&access_token={INSTAGRAM_ACCESS_TOKEN}"
        _, check = http("GET", check_url, timeout=15)
        status_code = check.get("status_code", "")
        print(f"[Instagram] Container status [{attempt+1}/30]: {status_code}")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            print(f"[Instagram] Processing error: {check}")
            return False

    # Publish
    pub_params = urllib.parse.urlencode({
        "creation_id": container_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    })
    pub_status, pub_resp = http(
        "POST",
        f"{IG_API_BASE}/{INSTAGRAM_USER_ID}/media_publish",
        data=pub_params.encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )

    if pub_status == 200 and "id" in pub_resp:
        print(f"[Instagram] Reel published! Media ID: {pub_resp['id']} ✓")
        return True

    print(f"[Instagram] Publish error {pub_status}: {pub_resp}")
    return False

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("H&C PRECISE LOGISTICS LLC — Reels Creator (D-ID)")
    print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    import tempfile, os

    # Pick topic by week number
    week = datetime.now(timezone.utc).isocalendar()[1]
    topic = REEL_TOPICS[week % len(REEL_TOPICS)]
    avatar_key = topic["avatar"]
    avatar_url = AVATAR_IMAGES[avatar_key]
    print(f"[Topic] {topic['title']} | Avatar: {avatar_key}")

    # Step 1: Generate script
    script = generate_script(topic)

    # Step 2: Create D-ID talking video
    talk_id = create_did_talk(avatar_url, script, avatar_key)
    if not talk_id:
        print("FATAL: D-ID talk creation failed")
        sys.exit(1)

    video_url_did = poll_did_talk(talk_id)
    if not video_url_did:
        print("FATAL: D-ID video render failed or timed out")
        sys.exit(1)

    # Step 3: Download and upload to GitHub Pages
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_video = os.path.join(tmp_dir, "reel.mp4")

        if not download_video(video_url_did, tmp_video):
            print("FATAL: could not download D-ID video")
            sys.exit(1)

        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        repo_path = f"videos/reel_{topic['id']}_{date_str}.mp4"
        public_url = upload_to_pages(tmp_video, repo_path)

    if not public_url:
        # Fallback: try using D-ID URL directly
        print("[Upload] GitHub Pages upload failed — trying D-ID URL directly")
        public_url = video_url_did

    # Wait for GitHub Pages CDN propagation
    if "github.io" in public_url:
        print("[Wait] Waiting 45s for GitHub Pages CDN...")
        time.sleep(45)

    # Step 4: Generate caption and post to Instagram
    caption = generate_reel_caption(topic, avatar_key)
    success = ig_post_reel(public_url, caption)

    if success:
        print(f"\n✓ Reel posted! Topic: {topic['id']} | Avatar: {avatar_key}")
    else:
        print(f"\n✗ Reel post failed")
        sys.exit(1)

if __name__ == "__main__":
    main()

"""
H&C PRECISE LOGISTICS LLC — Instagram Auto-Poster
GitHub Actions: runs Mon-Fri 9AM ET
Image priority: DALL-E 3 → FLUX.1 (HF) → Unsplash fallback
Caption: Claude claude-opus-4-5 via Anthropic API
Topic rotation: reads/writes used_topics.json via GitHub API
"""

import os
import json
import random
import base64
import urllib.request
import urllib.parse
import urllib.error
import time
import re
import sys
import hashlib
from datetime import datetime, timezone

# ── Secrets from GitHub Actions environment ──────────────────────────────────
INSTAGRAM_USER_ID      = os.environ["INSTAGRAM_USER_ID"]
INSTAGRAM_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
ANTHROPIC_API_KEY      = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY         = os.environ.get("OPENAI_API_KEY", "")
HF_TOKEN               = os.environ.get("HF_TOKEN", "")
GITHUB_TOKEN           = os.environ["GITHUB_TOKEN"]
GITHUB_REPO            = os.environ.get("GITHUB_REPOSITORY", "hcprelog/public-assets")

# ── Constants ─────────────────────────────────────────────────────────────────
IG_API_BASE    = "https://graph.facebook.com/v25.0"
TOPICS_FILE    = "automation/topics.json"
USED_FILE      = "automation/used_topics.json"
TOPIC_MEMORY   = 15   # avoid repeating any of last N topics
IMAGE_MEMORY   = 10   # avoid repeating any of last N Unsplash images
AVATAR_RATE    = 0.25 # 25% of posts use a brand avatar

# Permanent brand avatar images — upload once to repo via GitHub web UI
# Path: avatars/marcus-hale.jpg and avatars/arielle-grant.jpg
AVATAR_IMAGES = {
    "marcus":  "https://hcprelog.github.io/public-assets/avatars/marcus-hale.jpg",
    "arielle": "https://hcprelog.github.io/public-assets/avatars/arielle-grant.jpg",
    "dennis":  "https://hcprelog.github.io/public-assets/avatars/marcus-hale.jpg",  # fallback to marcus until dennis photo added
}

# Expanded Unsplash pool (20 images) — tracked to prevent repeats
UNSPLASH_IMAGES = [
    "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=1080&q=85",
    "https://images.unsplash.com/photo-1553413077-190dd305871c?w=1080&q=85",
    "https://images.unsplash.com/photo-1494412574643-ff11b0a5c1c3?w=1080&q=85",
    "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=1080&q=85",
    "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=1080&q=85",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1080&q=85",
    "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=1080&q=85",
    "https://images.unsplash.com/photo-1521791136064-7986c2920216?w=1080&q=85",
    "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1080&q=85",
    "https://images.unsplash.com/photo-1600880292203-757bb62b4baf?w=1080&q=85",
    "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=1080&q=85",
    "https://images.unsplash.com/photo-1556761175-4b46a572b786?w=1080&q=85",
    "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1080&q=85",
    "https://images.unsplash.com/photo-1568992687947-868a62a9f521?w=1080&q=85",
    "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=1080&q=85",
    "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=1080&q=85",
    "https://images.unsplash.com/photo-1431540015161-0bf868a2d407?w=1080&q=85",
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1080&q=85",
    "https://images.unsplash.com/photo-1572021335469-31706a17aaef?w=1080&q=85",
    "https://images.unsplash.com/photo-1664575602554-2087b04935a5?w=1080&q=85",
]

# ── HTTP helper ───────────────────────────────────────────────────────────────
def http(method, url, headers=None, data=None, timeout=45):
    headers = headers or {}
    if isinstance(data, dict):
        data = json.dumps(data).encode()
        headers.setdefault("Content-Type", "application/json")
    elif isinstance(data, str):
        data = data.encode()
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

# ═══════════════════════════════════════════════════════════════════════════════
# ITEM 3 — TOPIC ROTATION via GitHub API
# ═══════════════════════════════════════════════════════════════════════════════

def gh_get_file(path):
    """Returns (content_dict, sha) or (None, None)."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    status, resp = http("GET", url, headers=headers)
    if status == 200:
        content = base64.b64decode(resp["content"]).decode()
        return json.loads(content), resp["sha"]
    return None, None

def gh_put_file(path, content_dict, sha, message):
    """Commits updated JSON file back to the repo."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    encoded = base64.b64encode(json.dumps(content_dict, indent=2).encode()).decode()
    body = {"message": message, "content": encoded}
    if sha:
        body["sha"] = sha
    status, resp = http("PUT", url, headers=headers, data=body)
    return status in (200, 201)

def pick_topic():
    """Pick a topic not used in the last TOPIC_MEMORY posts."""
    topics_data, _ = gh_get_file(TOPICS_FILE)
    used_data, used_sha = gh_get_file(USED_FILE)

    if not topics_data:
        # Fallback: load bundled topics.json from local checkout
        with open("automation/topics.json") as f:
            topics_data = json.load(f)

    all_topics = topics_data["topics"]
    used_ids = (used_data or {}).get("used", [])
    recent_ids = set(used_ids[-TOPIC_MEMORY:])

    available = [t for t in all_topics if t["id"] not in recent_ids]
    if not available:
        available = all_topics  # full reset if all used

    chosen = random.choice(available)
    print(f"[Topic] Selected: {chosen['title']} (id={chosen['id']}, avatar={chosen['avatar']})")
    return chosen, used_data or {"used": []}, used_sha

def mark_topic_used(topic, image_url, image_source, used_data, used_sha):
    """Append topic ID and image URL to used lists and push back to repo."""
    used_data["used"].append(topic["id"])
    used_data["used"] = used_data["used"][-50:]

    # Track used images to prevent Unsplash repeats
    if image_source == "unsplash":
        used_images = used_data.get("used_images", [])
        used_images.append(image_url)
        used_data["used_images"] = used_images[-20:]

    used_data["last_posted"] = datetime.now(timezone.utc).isoformat()
    ok = gh_put_file(
        USED_FILE, used_data, used_sha,
        f"chore: mark topic used — {topic['id']} [{datetime.now(timezone.utc).strftime('%Y-%m-%d')}]"
    )
    if ok:
        print(f"[Topic] Rotation state saved ✓")
    else:
        print(f"[Topic] WARNING: could not save rotation state")

# ═══════════════════════════════════════════════════════════════════════════════
# ITEM 1 — IMAGE GENERATION: DALL-E 3 → FLUX.1 → Unsplash
# ═══════════════════════════════════════════════════════════════════════════════

def gen_image_dalle3(topic):
    """
    DALL-E 3 via OpenAI API.
    Requires API billing at platform.openai.com/account/billing
    (separate from ChatGPT Plus subscription — ~$0.04/image)
    """
    if not OPENAI_API_KEY:
        print("[Image] DALL-E 3: no API key, skipping")
        return None

    prompt = (
        f"Professional corporate stock photo for a government contracting company. "
        f"Theme: {topic['title']}. "
        f"Clean, modern, authoritative. Navy blue and white color scheme. "
        f"No text in the image. High quality business photography style. "
        f"1:1 square format."
    )
    print(f"[Image] Trying DALL-E 3...")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    body = {"model": "dall-e-3", "prompt": prompt, "n": 1, "size": "1024x1024", "quality": "standard"}
    status, resp = http("POST", "https://api.openai.com/v1/images/generations", headers=headers, data=body, timeout=60)

    if status == 200:
        url = resp["data"][0]["url"]
        print(f"[Image] DALL-E 3 success ✓")
        return url

    # Diagnose the specific error
    err = resp.get("error", {})
    code = err.get("code", "")
    msg  = err.get("message", str(resp))

    if status == 429 or "billing" in msg.lower() or "quota" in msg.lower() or code == "insufficient_quota":
        print(f"[Image] DALL-E 3: API billing not active on platform.openai.com")
        print(f"[Image]   Fix: platform.openai.com/account/billing → Add $5 credit")
        print(f"[Image]   Note: ChatGPT Plus does NOT include API access — these are separate billing accounts")
    elif status == 401:
        print(f"[Image] DALL-E 3: invalid API key — rotate at platform.openai.com/api-keys")
    else:
        print(f"[Image] DALL-E 3 error {status}: {msg}")

    return None

def gen_image_flux(topic):
    """
    FLUX.1-schnell via Hugging Face Inference API.
    Free tier: ~500 requests/day. Cold start: 15-45s.
    """
    if not HF_TOKEN:
        print("[Image] FLUX.1: no HF token, skipping")
        return None

    prompt = (
        f"Professional business photo, government contracting theme, {topic['title']}, "
        f"navy blue color scheme, clean modern corporate aesthetic, no text, 1:1 ratio"
    )

    # Try fast model first, then fall back to stable model
    models = [
        "black-forest-labs/FLUX.1-schnell",
        "stabilityai/stable-diffusion-xl-base-1.0",
    ]

    for model in models:
        print(f"[Image] Trying FLUX via {model.split('/')[-1]}...")
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        body = json.dumps({"inputs": prompt, "parameters": {"num_inference_steps": 4, "guidance_scale": 0}}).encode()

        try:
            req = urllib.request.Request(url, data=body, headers={**headers, "Content-Type": "application/json"}, method="POST")
            # Use longer timeout for cold model load
            with urllib.request.urlopen(req, timeout=90) as r:
                if r.status == 200:
                    content_type = r.headers.get("Content-Type", "")
                    if "image" in content_type:
                        # HF returns raw image bytes — host on GitHub Pages
                        img_bytes = r.read()
                        img_url = upload_image_to_pages(img_bytes, topic["id"])
                        if img_url:
                            print(f"[Image] FLUX.1 success ✓ → {img_url}")
                            return img_url
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode()
            if e.code == 503:
                print(f"[Image] FLUX model loading, waiting 20s...")
                time.sleep(20)
                # retry once
                try:
                    req2 = urllib.request.Request(url, data=body, headers={**headers, "Content-Type": "application/json"}, method="POST")
                    with urllib.request.urlopen(req2, timeout=90) as r2:
                        if r2.status == 200 and "image" in r2.headers.get("Content-Type",""):
                            img_bytes = r2.read()
                            img_url = upload_image_to_pages(img_bytes, topic["id"])
                            if img_url:
                                print(f"[Image] FLUX.1 success after retry ✓")
                                return img_url
                except Exception:
                    pass
            else:
                print(f"[Image] FLUX {e.code}: {body_txt[:200]}")
        except Exception as ex:
            print(f"[Image] FLUX connection error: {ex}")

    return None

def upload_image_to_pages(img_bytes, topic_id):
    """
    Commit raw image bytes to repo's images/ folder so GitHub Pages serves it publicly.
    Returns the public GitHub Pages URL.
    """
    filename  = f"images/ig_{topic_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jpg"
    pages_url = f"https://hcprelog.github.io/public-assets/{filename}"
    gh_url    = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers   = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    encoded   = base64.b64encode(img_bytes).decode()
    body      = {"message": f"auto: generated image {filename}", "content": encoded}
    status, _ = http("PUT", gh_url, headers=headers, data=body, timeout=30)
    if status in (200, 201):
        return pages_url
    print(f"[Image] GitHub Pages upload failed: {status}")
    return None

def pick_unsplash_image(used_data):
    """
    Pick an Unsplash image not used in the last IMAGE_MEMORY posts.
    Tracks used images in used_topics.json to prevent repeats.
    """
    used_images = used_data.get("used_images", [])
    recent = set(used_images[-IMAGE_MEMORY:])
    available = [u for u in UNSPLASH_IMAGES if u not in recent]
    if not available:
        available = UNSPLASH_IMAGES  # full reset if all used
    url = random.choice(available)
    print(f"[Image] Using Unsplash (pool={len(available)} available)")
    return url

def get_avatar_image(topic):
    """
    Return the avatar URL for this topic's assigned avatar.
    Only used AVATAR_RATE (25%) of the time.
    """
    avatar_key = topic.get("avatar", "arielle")
    url = AVATAR_IMAGES.get(avatar_key, AVATAR_IMAGES["arielle"])
    print(f"[Image] Using brand avatar: {avatar_key}")
    return url

def get_image(topic, used_data):
    """
    Image selection logic:
    - 25% of posts: use brand avatar (Marcus or Arielle)
    - 75% of posts: DALL-E 3 → Unsplash (no repeats)
    """
    # 25% avatar roll
    if random.random() < AVATAR_RATE:
        url = get_avatar_image(topic)
        return url, "avatar"

    # 75%: try DALL-E 3 first
    url = gen_image_dalle3(topic)
    if url:
        return url, "dalle3"

    # Unsplash with repeat-prevention
    url = pick_unsplash_image(used_data)
    return url, "unsplash"

# ═══════════════════════════════════════════════════════════════════════════════
# CAPTION GENERATION — Claude claude-opus-4-5
# ═══════════════════════════════════════════════════════════════════════════════

AVATAR_VOICES = {
    "marcus": (
        "Marcus Hale, GovCon Operations Advisor for H&C PRECISE LOGISTICS LLC. "
        "Direct, credible, experienced tone. Speak like a seasoned federal contractor who has seen contracts won and lost. "
        "No fluff. Practical insights."
    ),
    "arielle": (
        "Arielle Grant, Business Growth Advisor for H&C PRECISE LOGISTICS LLC. "
        "Warm, encouraging, practical tone. Speak like a knowledgeable guide helping businesses take their first steps. "
        "Accessible and clear."
    ),
    "dennis": (
        "Dennis Hunter, President and CEO of H&C PRECISE LOGISTICS LLC, SDVOSB veteran founder. "
        "Authentic, mission-driven, authoritative. Speak from personal experience as a veteran who built this company."
    ),
}

def generate_caption(topic):
    if not ANTHROPIC_API_KEY:
        return fallback_caption(topic)

    voice = AVATAR_VOICES.get(topic.get("avatar", "arielle"), AVATAR_VOICES["arielle"])
    system = (
        f"You are {voice} "
        f"Company: H&C PRECISE LOGISTICS LLC (SDVOSB + HubZone certified, Durham NC). "
        f"Website: hcprelog.com. Contact: hcprelog@gmail.com. "
        f"RULES: Always use 'H&C PRECISE LOGISTICS LLC' — exact caps. "
        f"Never use old phone (555) or old domain hcpreciselogistics.com. "
        f"End every post with: hcprelog.com"
    )
    user = (
        f"Write an Instagram caption for this topic: '{topic['title']}'\n"
        f"Hook to use: '{topic['hook']}'\n\n"
        f"Requirements:\n"
        f"- Start with the hook (adapt it naturally)\n"
        f"- 3-5 bullet points of concrete insight\n"
        f"- 1 clear CTA (drive to hcprelog.com or mention a specific offer)\n"
        f"- 15-20 relevant hashtags at the end\n"
        f"- Total length: 200-300 words\n"
        f"- No emojis in bullet points — only 1-2 emojis max total\n"
        f"- Professional but human\n"
    )

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-opus-4-5",
        "max_tokens": 1024,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    status, resp = http("POST", "https://api.anthropic.com/v1/messages", headers=headers, data=body, timeout=30)
    if status == 200:
        caption = resp["content"][0]["text"].strip()
        print(f"[Caption] Generated via Claude ({len(caption)} chars)")
        return caption
    print(f"[Caption] Claude error {status}: {resp}")
    return fallback_caption(topic)

def fallback_caption(topic):
    return (
        f"{topic['hook']}\n\n"
        f"H&C PRECISE LOGISTICS LLC helps businesses navigate government contracting — "
        f"from SAM.gov registration to contract execution.\n\n"
        f"SDVOSB + HubZone certified. Durham, NC.\n\n"
        f"Learn more: hcprelog.com\n\n"
        f"#GovCon #FederalContracting #SDVOSB #HubZone #SmallBusiness #VeteranOwned "
        f"#GovernmentContracting #HCPreciseLogistics #DurhamNC"
    )

# ═══════════════════════════════════════════════════════════════════════════════
# INSTAGRAM GRAPH API — POST
# ═══════════════════════════════════════════════════════════════════════════════

def ig_post(image_url, caption):
    """Create container then publish to Instagram."""
    print(f"\n[Instagram] Creating media container...")
    print(f"[Instagram] Image URL: {image_url[:80]}...")

    # Step 1: Create container
    params = urllib.parse.urlencode({
        "image_url": image_url,
        "caption": caption,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    })
    url = f"{IG_API_BASE}/{INSTAGRAM_USER_ID}/media"
    status, resp = http("POST", url, data=params.encode(),
                        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)

    if status != 200 or "id" not in resp:
        print(f"[Instagram] Container error {status}: {resp}")
        return False

    container_id = resp["id"]
    print(f"[Instagram] Container created: {container_id}")

    # Step 2: Wait for container to be ready
    print("[Instagram] Checking container status...")
    for attempt in range(6):
        time.sleep(5)
        check_url = f"{IG_API_BASE}/{container_id}?fields=status_code&access_token={INSTAGRAM_ACCESS_TOKEN}"
        _, check = http("GET", check_url, timeout=15)
        status_code = check.get("status_code", "")
        print(f"[Instagram] Container status: {status_code}")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            print(f"[Instagram] Container error — image URL may not be accessible")
            return False

    # Step 3: Publish
    print("[Instagram] Publishing...")
    pub_params = urllib.parse.urlencode({
        "creation_id": container_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    })
    pub_url = f"{IG_API_BASE}/{INSTAGRAM_USER_ID}/media_publish"
    pub_status, pub_resp = http("POST", pub_url, data=pub_params.encode(),
                                headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)

    if pub_status == 200 and "id" in pub_resp:
        print(f"[Instagram] Posted successfully! Media ID: {pub_resp['id']} ✓")
        return True

    print(f"[Instagram] Publish error {pub_status}: {pub_resp}")
    return False

# ═══════════════════════════════════════════════════════════════════════════════
# ITEM 2 — VIDEO PIPELINE TRIGGER
# Handled by instagram-reel.yml workflow (runs create_reel.py weekly)
# This function just logs that the video workflow is separate
# ═══════════════════════════════════════════════════════════════════════════════

def log_video_pipeline_status():
    print("\n[Video] Video Reels handled by instagram-reel.yml (runs Wednesdays)")
    print("[Video] See automation/create_reel.py for the video pipeline")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("H&C PRECISE LOGISTICS LLC — Instagram Auto-Poster")
    print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Step 1: Pick topic (Item 3 — rotation)
    topic, used_data, used_sha = pick_topic()

    # Step 2: Generate image (Item 1 — Avatar 25% / DALL-E 3 / Unsplash)
    image_url, image_source = get_image(topic, used_data)
    print(f"[Image] Source: {image_source} | URL: {image_url[:80]}...")

    # Step 3: Generate caption
    caption = generate_caption(topic)

    # Step 4: Post to Instagram
    success = ig_post(image_url, caption)

    # Step 5: Mark topic as used (only if post succeeded)
    if success:
        mark_topic_used(topic, image_url, image_source, used_data, used_sha)
        print(f"\n✓ Post complete | Topic: {topic['id']} | Image: {image_source}")
    else:
        print(f"\n✗ Post failed — topic NOT marked used, will retry tomorrow")
        sys.exit(1)

    # Step 6: Log video pipeline
    log_video_pipeline_status()

if __name__ == "__main__":
    main()

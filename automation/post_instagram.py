"""
H&C PRECISE LOGISTICS LLC — Instagram + Facebook Auto-Poster
GitHub Actions: runs Mon-Fri 9AM ET

Image priority: GPT Image 1 (JPEG) -> FLUX.1 (HF) -> Unsplash fallback
Caption:        Claude claude-opus-4-5 via Anthropic API
Topic rotation: reads/writes used_topics.json via GitHub API
Publishes to:   Instagram Feed + Facebook Page (FB is skipped if secrets absent)

──────────────────────────────────────────────────────────────────────────────
2026-07-29 OUTAGE FIX — read before changing image handling
──────────────────────────────────────────────────────────────────────────────
Runs #47/#48/#49 (Mon-Wed 07-27..07-29) all failed with:

    Instagram container error 400 — 'Only photo or video can be accepted as
    media type.'  code 9004 / error_subcode 2207052

Root cause: the 2026-07-26 migration from dall-e-3 to gpt-image-1 changed the
returned image format. gpt-image-1 returns base64 PNG by default, but
upload_image_to_pages() hardcoded a ".jpg" filename. GitHub Pages then served
PNG bytes under Content-Type: image/jpeg. Instagram's Graph API accepts JPEG
ONLY, inspects the real bytes, and rejects the mismatch.

Verified against the live file that Instagram refused:
    ig_networking-events_20260729.jpg -> HTTP 200, served image/jpeg,
    magic bytes 89 50 4E 47 = PNG.

Why it wasn't caught: run #46 was DRY_RUN=true, and the dry-run branch returns
BEFORE ig_post() is ever called. A dry run structurally cannot validate an
image-format change.

>>> RULE: never trust a file extension. Sniff the real bytes (_sniff_format)
>>> before upload, and validate any image-pipeline change with ONE REAL POST,
>>> never with a dry run.
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
INSTAGRAM_USER_ID = os.environ["INSTAGRAM_USER_ID"]
INSTAGRAM_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "hcprelog/public-assets")
DRY_RUN = os.environ.get("DRY_RUN", "").strip().lower() in ("true", "1", "yes")

# Facebook Page cross-posting. Optional — if either is unset, FB is skipped
# cleanly and Instagram still posts. Add these as repo secrets to enable.
FACEBOOK_PAGE_ID = os.environ.get("FACEBOOK_PAGE_ID", "").strip()
FACEBOOK_PAGE_TOKEN = os.environ.get("FACEBOOK_PAGE_TOKEN", "").strip()

# ── Constants ─────────────────────────────────────────────────────────────────
IG_API_BASE = "https://graph.facebook.com/v25.0"
FB_API_BASE = "https://graph.facebook.com/v25.0"
TOPICS_FILE = "automation/topics.json"
USED_FILE = "automation/used_topics.json"
TOPIC_MEMORY = 15   # avoid repeating any of last N topics
IMAGE_MEMORY = 10   # avoid repeating any of last N Unsplash images

# ──────────────────────────────────────────────────────────────────────────────
# IMAGERY POLICY — updated 2026-07-29 by President Hunter
# ──────────────────────────────────────────────────────────────────────────────
# The named AI brand presenters (Marcus Hale, Arielle Grant) are VIDEO-ONLY and
# must NEVER be posted as stills. That rule stands from 2026-07-14, when a
# Marcus Hale headshot auto-posted to the live feed and had to be deleted.
#
# What President Hunter authorised on 2026-07-29 is DIFFERENT and narrower:
# generic, unnamed, AI-generated professionals appearing in ordinary corporate
# stock-style photography, so the feed shows fresh faces between his own
# Marcus/Arielle video posts. These are anonymous stock people — they are never
# named, never given a voice, never presented as staff, founders, or presenters.
#
# The old AVATAR_IMAGES / AVATAR_RATE mechanism is REMOVED outright so the
# named-presenter files are unreachable from this script by construction.
#
# PERSON_SCENES  -> generic professionals (the "new faces")
# ENVIRONMENT_SCENES -> warehouse / office / facility scenes, no people
PERSON_RATE = 0.5   # ~half the generated posts feature anonymous people

PERSON_SCENES = [
    "a confident professional in business attire standing in a bright modern office lobby, "
    "arms relaxed, natural window light, shallow depth of field",
    "two colleagues in business attire reviewing documents together at a conference table, "
    "bright meeting room, glass wall behind them, candid working moment",
    "a professional in a hard hat and safety vest with a tablet on a clean warehouse floor, "
    "high racking and pallets softly out of focus behind them",
    "a professional seated at a desk reviewing paperwork, focused expression, "
    "warm afternoon light through blinds, monitor glow in the background",
    "a small team walking through a modern facility corridor mid-conversation, "
    "motion and energy, clean industrial architecture",
    "a professional shaking hands with a colleague in an office setting, "
    "warm natural light, genuine expression, business partnership moment",
]

ENVIRONMENT_SCENES = [
    "a clean, well-organized warehouse interior with high racking, pallets and "
    "polished concrete floors, dramatic overhead lighting, no people",
    "a modern corporate office interior, empty conference room with glass walls "
    "and a long table, early morning light, no people",
    "a loading dock with roll-up doors and staged freight pallets, "
    "late afternoon light raking across the floor, no people",
    "an organized facility maintenance area with neatly stored equipment, "
    "clean and professional, no people",
    "an aerial view of a distribution center and truck yard at golden hour, no people",
    "a tidy government-style office workspace with filing systems and documents "
    "arranged on a desk, no people",
]

# Expanded Unsplash pool (20 images) — tracked to prevent repeats.
# NOTE: Unsplash serves JPEG, so these are always Instagram-safe.
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
    "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=1080&q=85",
    "https://images.unsplash.com/photo-1431540015161-0bf868a2d407?w=1080&q=85",
    "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=1080&q=85",
    "https://images.unsplash.com/photo-1572021335469-31706a17aaef?w=1080&q=85",
    "https://images.unsplash.com/photo-1664575602554-2087b04935a5?w=1080&q=85",
    "https://images.unsplash.com/photo-1454165833767-1ba26ed57ef2?w=1080&q=85",
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
# TOPIC ROTATION via GitHub API
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
        with open("automation/topics.json") as f:
            topics_data = json.load(f)

    all_topics = topics_data["topics"]
    used_ids = (used_data or {}).get("used", [])
    recent_ids = set(used_ids[-TOPIC_MEMORY:])

    available = [t for t in all_topics if t["id"] not in recent_ids]
    if not available:
        available = all_topics  # full reset if all used

    chosen = random.choice(available)
    print(f"[Topic] Selected: {chosen['title']} (id={chosen['id']})")
    return chosen, used_data or {"used": []}, used_sha


def mark_topic_used(topic, image_url, image_source, used_data, used_sha):
    """Append topic ID and image URL to used lists and push back to repo."""
    used_data["used"].append(topic["id"])
    used_data["used"] = used_data["used"][-50:]

    if image_source == "unsplash":
        used_images = used_data.get("used_images", [])
        used_images.append(image_url)
        used_data["used_images"] = used_images[-20:]

    used_data["last_posted"] = datetime.now(timezone.utc).isoformat()
    ok = gh_put_file(
        USED_FILE, used_data, used_sha,
        f"chore: mark topic used — {topic['id']} [{datetime.now(timezone.utc).strftime('%Y-%m-%d')}]"
    )
    print("[Topic] Rotation state saved ✓" if ok else "[Topic] WARNING: could not save rotation state")


# ═══════════════════════════════════════════════════════════════════════════════
# IMAGE GENERATION — GPT Image 1 (JPEG) -> FLUX.1 -> Unsplash
# ═══════════════════════════════════════════════════════════════════════════════

def _sniff_format(img_bytes):
    """
    Identify the REAL image format from magic bytes. Never trust a filename.
    This is the guard that would have prevented the 2026-07-29 outage.
    """
    if img_bytes[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if img_bytes[:4] == b"\x89PNG":
        return "png"
    if img_bytes[:4] == b"RIFF" and img_bytes[8:12] == b"WEBP":
        return "webp"
    if img_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    return "unknown"


def build_image_prompt(topic):
    """
    Compose the image prompt. Alternates between anonymous professionals
    ("new faces", per President Hunter 2026-07-29) and people-free facility
    scenes, so the grid does not become monotonous.

    Never references or resembles Marcus Hale or Arielle Grant — those are
    video-only named presenters and are deliberately unreachable from here.
    """
    if random.random() < PERSON_RATE:
        scene = random.choice(PERSON_SCENES)
        kind = "person"
    else:
        scene = random.choice(ENVIRONMENT_SCENES)
        kind = "environment"

    prompt = (
        f"Professional corporate stock photograph for a government contracting and "
        f"logistics company. Scene: {scene}. "
        f"Contextual theme: {topic['title']}. "
        f"Photorealistic, shot on a full-frame camera, natural lighting, crisp detail, "
        f"muted navy blue and white corporate colour palette. "
        f"Absolutely no text, no words, no letters, no logos, no watermarks anywhere in the image. "
        f"Square 1:1 composition."
    )
    return prompt, kind


def gen_image_openai(topic):
    """
    GPT Image 1 via OpenAI API (dall-e-3 was retired by OpenAI on 2026-05-12).

    CRITICAL: output_format MUST be "jpeg". gpt-image-1 defaults to PNG, and
    Instagram's Graph API accepts JPEG only — that mismatch caused the
    2026-07-27..29 outage. Do not remove this parameter.
    """
    if not OPENAI_API_KEY:
        print("[Image] GPT Image 1: no API key, skipping")
        return None, None

    prompt, kind = build_image_prompt(topic)
    print(f"[Image] Trying GPT Image 1 (scene type: {kind})...")

    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    body = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024",
        "quality": "high",
        "output_format": "jpeg",   # ← REQUIRED. See module docstring.
    }
    status, resp = http("POST", "https://api.openai.com/v1/images/generations",
                        headers=headers, data=body, timeout=120)

    if status == 200:
        b64 = resp["data"][0]["b64_json"]
        img_bytes = base64.b64decode(b64)
        img_url = upload_image_to_pages(img_bytes, topic["id"])
        if img_url:
            print(f"[Image] GPT Image 1 success ✓ → {img_url}")
            return img_url, kind
        print("[Image] GPT Image 1: generated but upload/validation failed")
        return None, None

    err = resp.get("error", {})
    code = err.get("code", "")
    msg = err.get("message", str(resp))

    if status == 429 or "billing" in msg.lower() or "quota" in msg.lower() or code == "insufficient_quota":
        print("[Image] GPT Image 1: API billing not active on platform.openai.com")
        print("[Image] Fix: platform.openai.com/account/billing → Add credit")
        print("[Image] Note: ChatGPT Plus does NOT include API access — separate billing")
    elif status == 401:
        print("[Image] GPT Image 1: invalid API key — rotate at platform.openai.com/api-keys")
    else:
        print(f"[Image] GPT Image 1 error {status}: {msg}")

    return None, None


def gen_image_flux(topic):
    """FLUX.1-schnell via Hugging Face Inference API. Free tier, cold start 15-45s."""
    if not HF_TOKEN:
        print("[Image] FLUX.1: no HF token, skipping")
        return None

    prompt, _ = build_image_prompt(topic)
    models = ["black-forest-labs/FLUX.1-schnell", "stabilityai/stable-diffusion-xl-base-1.0"]

    for model in models:
        print(f"[Image] Trying FLUX via {model.split('/')[-1]}...")
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
        body = json.dumps({"inputs": prompt,
                           "parameters": {"num_inference_steps": 4, "guidance_scale": 0}}).encode()
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=90) as r:
                if r.status == 200 and "image" in r.headers.get("Content-Type", ""):
                    img_url = upload_image_to_pages(r.read(), topic["id"])
                    if img_url:
                        print(f"[Image] FLUX.1 success ✓ → {img_url}")
                        return img_url
        except urllib.error.HTTPError as e:
            body_txt = e.read().decode()
            if e.code == 503:
                print("[Image] FLUX model loading, waiting 20s...")
                time.sleep(20)
                try:
                    req2 = urllib.request.Request(url, data=body, headers=headers, method="POST")
                    with urllib.request.urlopen(req2, timeout=90) as r2:
                        if r2.status == 200 and "image" in r2.headers.get("Content-Type", ""):
                            img_url = upload_image_to_pages(r2.read(), topic["id"])
                            if img_url:
                                print("[Image] FLUX.1 success after retry ✓")
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
    Commit raw image bytes to the repo's images/ folder for GitHub Pages hosting.

    Instagram's Graph API accepts JPEG ONLY. Anything else is rejected at the
    container step with code 9004 / subcode 2207052. So we verify the ACTUAL
    bytes here rather than trusting the extension we are about to write.
    """
    fmt = _sniff_format(img_bytes)
    if fmt != "jpeg":
        print(f"[Image] REJECTED: generator returned {fmt.upper()}, Instagram requires JPEG.")
        print("[Image] Falling back to the next image source rather than uploading an unusable file.")
        return None

    filename = f"images/ig_{topic_id}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jpg"
    pages_url = f"https://hcprelog.github.io/public-assets/{filename}"
    gh_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{filename}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    body = {
        "message": f"auto: generated image {filename}",
        "content": base64.b64encode(img_bytes).decode(),
    }

    # If a run earlier the same day already wrote this path, GitHub requires the
    # existing blob SHA to overwrite it — otherwise the PUT fails with 409.
    st, existing = http("GET", gh_url, headers=headers)
    if st == 200 and isinstance(existing, dict) and existing.get("sha"):
        body["sha"] = existing["sha"]

    status, _ = http("PUT", gh_url, headers=headers, data=body, timeout=30)
    if status in (200, 201):
        print(f"[Image] Uploaded verified JPEG ({len(img_bytes):,} bytes) → {pages_url}")
        return pages_url

    print(f"[Image] GitHub Pages upload failed: {status}")
    return None


def pick_unsplash_image(used_data):
    """Pick an Unsplash image not used in the last IMAGE_MEMORY posts."""
    used_images = used_data.get("used_images", [])
    recent = set(used_images[-IMAGE_MEMORY:])
    available = [u for u in UNSPLASH_IMAGES if u not in recent]
    if not available:
        available = UNSPLASH_IMAGES
    url = random.choice(available)
    print(f"[Image] Using Unsplash (pool={len(available)} available)")
    return url


def get_image(topic, used_data):
    """GPT Image 1 (JPEG) -> FLUX.1 -> Unsplash. All paths must yield JPEG."""
    url, kind = gen_image_openai(topic)
    if url:
        return url, f"gpt-image-1/{kind}"

    url = gen_image_flux(topic)
    if url:
        return url, "flux"

    return pick_unsplash_image(used_data), "unsplash"


# ═══════════════════════════════════════════════════════════════════════════════
# CAPTION GENERATION — Claude claude-opus-4-5
# ═══════════════════════════════════════════════════════════════════════════════

# Hard compliance guardrails. These mirror the standing content-accuracy rules
# and exist because captions publish automatically with no human review.
BRAND_GUARDRAILS = (
    "STRICT FACTUAL RULES — never violate these:\n"
    "- Company name is exactly 'H&C PRECISE LOGISTICS LLC'.\n"
    "- Business address is Durham, NC. NEVER say Norlina.\n"
    "- Certifications you MAY claim: SDVOSB (VA-verified), HUBZone (SBA-certified), "
    "Federal Prime Contractor. MBE may ONLY be described as 'in progress', never 'certified'.\n"
    "- NEVER claim: DOT licensed, 8(a), WOSB, or any guarantee of winning contracts.\n"
    "- NEVER reference the VA Grand Junction contract as a completed or successful win.\n"
    "- If Hunter is named, he is 'President Hunter' — never 'Dennis Hunter' or a first name alone.\n"
    "- H&C was founded by two disabled veterans. Do not name the co-founder.\n"
    "- Do not invent client names, contract values, dollar figures, or statistics.\n"
    "- Never use a (555) phone number or the old domain hcpreciselogistics.com.\n"
)


def generate_caption(topic):
    if not ANTHROPIC_API_KEY:
        return fallback_caption(topic)

    system = (
        "You write Instagram and Facebook captions for H&C PRECISE LOGISTICS LLC, "
        "a Service-Disabled Veteran-Owned Small Business and HUBZone-certified federal "
        "prime contractor based in Durham, NC. Website hcprelog.com, email hcprelog@gmail.com. "
        "Voice: direct, credible, practical — a seasoned federal contractor who has seen "
        "contracts won and lost. No fluff, no hype, no hollow motivation.\n\n"
        + BRAND_GUARDRAILS +
        "\nEnd every post with: 🔗 Link in bio"
    )
    user = (
        f"Write a caption for this topic: '{topic['title']}'\n"
        f"Hook to use: '{topic['hook']}'\n\n"
        f"Requirements:\n"
        f"- Open with the hook, adapted naturally\n"
        f"- 3-5 bullet points of concrete, specific insight a contractor could act on\n"
        f"- 1 clear CTA driving to hcprelog.com\n"
        f"- 15-20 relevant hashtags, inline at the very end of the caption text "
        f"(NOT on a separate 'Hashtags:' line — it must be one copy-paste block)\n"
        f"- Total 200-300 words\n"
        f"- At most 1-2 emojis in the whole post; none in the bullets\n"
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
    status, resp = http("POST", "https://api.anthropic.com/v1/messages",
                        headers=headers, data=body, timeout=45)
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
        f"SDVOSB + HUBZone certified. Durham, NC.\n\n"
        f"Learn more — link in bio 🔗 "
        f"#GovCon #FederalContracting #SDVOSB #HubZone #SmallBusiness #VeteranOwned "
        f"#GovernmentContracting #HCPreciseLogistics #DurhamNC"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLISHING
# ═══════════════════════════════════════════════════════════════════════════════

def wait_for_image_url(image_url, attempts=40, delay=15):
    """
    GitHub Pages must finish rebuilding before Instagram can fetch the URL.
    Pages deploys have been taking 45-60s normally, but spiked to 2m43s-7m59s on 2026-08-06/07 (see pages-build-deployment run history). Budget widened 2026-08-08 to attempts=40 x delay=15s (~10 min) to cover that worst case with margin. Poll instead of assuming.
    """
    if "hcprelog.github.io" not in image_url:
        return True  # Unsplash and other hosts are already live

    for attempt in range(attempts):
        try:
            req = urllib.request.Request(image_url, method="HEAD")
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status == 200:
                    print(f"[Publish] Image URL live after ~{attempt * delay}s ✓")
                    return True
        except Exception:
            pass
        print(f"[Publish] Waiting for GitHub Pages… ({attempt + 1}/{attempts})")
        time.sleep(delay)

    print("[Publish] Image URL never became reachable — aborting.")
    return False


def ig_post(image_url, caption):
    """Create a media container, wait for it to finish, then publish."""
    print("\n[Instagram] Creating media container...")
    print(f"[Instagram] Image URL: {image_url[:80]}...")

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
        # Surface the classic format failure loudly so it is never misdiagnosed again.
        err = resp.get("error", {}) if isinstance(resp, dict) else {}
        if err.get("error_subcode") == 2207052 or err.get("code") == 9004:
            print("[Instagram] >>> This is the JPEG/PNG mismatch failure. The image at the URL "
                  "above is not a real JPEG. Check _sniff_format() and the generator's "
                  "output_format parameter. See module docstring.")
        return False

    container_id = resp["id"]
    print(f"[Instagram] Container created: {container_id}")

    print("[Instagram] Checking container status...")
    for _ in range(6):
        time.sleep(5)
        check_url = f"{IG_API_BASE}/{container_id}?fields=status_code&access_token={INSTAGRAM_ACCESS_TOKEN}"
        _, check = http("GET", check_url, timeout=15)
        status_code = check.get("status_code", "")
        print(f"[Instagram] Container status: {status_code}")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            print("[Instagram] Container error — image URL may not be accessible")
            return False

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


def fb_post(image_url, caption):
    """
    Publish the same image + caption to the Facebook Page.

    Optional by design: if FACEBOOK_PAGE_ID / FACEBOOK_PAGE_TOKEN are not set,
    this skips cleanly and never blocks the Instagram post. A Facebook failure
    is logged but does NOT fail the run, because Instagram is the primary
    channel and the topic has already been consumed by then.
    """
    if not FACEBOOK_PAGE_ID or not FACEBOOK_PAGE_TOKEN:
        print("\n[Facebook] Skipped — FACEBOOK_PAGE_ID / FACEBOOK_PAGE_TOKEN not configured.")
        print("[Facebook] Add both as repo secrets to enable Facebook cross-posting.")
        return None

    print("\n[Facebook] Posting photo to Page...")
    params = urllib.parse.urlencode({
        "url": image_url,
        "caption": caption,
        "access_token": FACEBOOK_PAGE_TOKEN,
    })
    url = f"{FB_API_BASE}/{FACEBOOK_PAGE_ID}/photos"
    status, resp = http("POST", url, data=params.encode(),
                        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=45)

    if status == 200 and ("id" in resp or "post_id" in resp):
        print(f"[Facebook] Posted successfully! Post ID: {resp.get('post_id', resp.get('id'))} ✓")
        return True

    print(f"[Facebook] Post error {status}: {resp}")
    print("[Facebook] Instagram post is unaffected. Check the Page token scope "
          "(needs pages_manage_posts) and that the token has not expired.")
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("H&C PRECISE LOGISTICS LLC — Instagram + Facebook Auto-Poster")
    print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    topic, used_data, used_sha = pick_topic()
    image_url, image_source = get_image(topic, used_data)
    print(f"[Image] Source: {image_source} | URL: {image_url[:80]}...")

    caption = generate_caption(topic)

    if DRY_RUN:
        print("\n[DRY RUN] Skipping real posts and topic-rotation commit.")
        print("[DRY RUN] ⚠ A dry run does NOT validate image format — the Instagram")
        print("[DRY RUN]   container step is skipped entirely. Validate image-pipeline")
        print("[DRY RUN]   changes with one real post. See module docstring.")
        print(f"[DRY RUN] Image ({image_source}): {image_url}")
        print(f"[DRY RUN] Caption preview ({len(caption)} chars):\n{caption[:300]}")
        print(f"\n✓ DRY RUN complete | Topic: {topic['id']} | Image: {image_source}")
        return

    if not wait_for_image_url(image_url):
        print("\n✗ Post failed — image URL unreachable, topic NOT marked used")
        sys.exit(1)

    success = ig_post(image_url, caption)

    if success:
        fb_result = fb_post(image_url, caption)
        mark_topic_used(topic, image_url, image_source, used_data, used_sha)
        fb_note = {True: "posted", False: "FAILED", None: "not configured"}[fb_result]
        print(f"\n✓ Post complete | Topic: {topic['id']} | Image: {image_source} | Facebook: {fb_note}")
    else:
        print("\n✗ Post failed — topic NOT marked used, will retry tomorrow")
        sys.exit(1)


if __name__ == "__main__":
    main()

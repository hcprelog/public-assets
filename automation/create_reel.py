"""
H&C PRECISE LOGISTICS LLC — Instagram Reels Creator (OpenAI TTS + Replicate SadTalker)
Runs weekly (Wednesdays 10AM ET) via instagram-reel.yml

Pipeline:
1. Pick a weekly Reel topic (Marcus or Arielle)
2. Generate 30-45 second talking script via Claude
3. Generate audio via OpenAI TTS tts-1-hd (primary) or edge-tts fallback
4. Upload audio to GitHub repo → raw URL (immediate, no CDN wait)
5. Send avatar image + audio to Replicate SadTalker → talking head MP4 (~$0.50/video)
6. Download MP4, upload to GitHub Pages → public URL
7. Post as Instagram Reel via Graph API

Cost: ~$0.52/video (Replicate + OpenAI TTS). No watermarks.
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
REPLICATE_API_TOKEN    = os.environ["REPLICATE_API_TOKEN"]
OPENAI_API_KEY         = os.environ.get("OPENAI_API_KEY", "")
GITHUB_TOKEN           = os.environ["GITHUB_TOKEN"]
GITHUB_REPO            = os.environ.get("GITHUB_REPOSITORY", "hcprelog/public-assets")

IG_API_BASE = "https://graph.facebook.com/v25.0"

# ── Brand avatars ─────────────────────────────────────────────────────────────
AVATAR_IMAGES = {
    "marcus":  "https://raw.githubusercontent.com/hcprelog/public-assets/main/avatars/Marcus%20Hale.png",
    "arielle": "https://raw.githubusercontent.com/hcprelog/public-assets/main/avatars/Arielle%20Grant.png",
}

# OpenAI TTS voices (primary — human-quality, natural)
OPENAI_VOICES = {
    "marcus":  "onyx",   # deep, authoritative American male
    "arielle": "nova",   # warm, natural American female
}

# edge-tts fallback voices (Microsoft Neural TTS — free, used if OpenAI fails)
EDGETTS_VOICES = {
    "marcus":  "en-US-ChristopherNeural",
    "arielle": "en-US-AriaNeural",
}

# Acronym expansion — TTS will mispronounce these if left as-is
ACRONYM_MAP = {
    "SDVOSB":       "Service-Disabled Veteran-Owned Small Business",
    "HubZone":      "Hub Zone",
    "GovCon":       "government contracting",
    "SAM.gov":      "SAM dot gov",
    "DoD":          "Department of Defense",
    "NAICS":        "NAY-icks",
    "RFP":          "Request for Proposal",
    "PWS":          "Performance Work Statement",
    "SBA":          "Small Business Administration",
    "CTA":          "call to action",
    "hcprelog.com": "H C prelog dot com",
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

# ── HTTP helpers ──────────────────────────────────────────────────────────────
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

def http_binary(method, url, headers=None, data=None, timeout=60):
    """HTTP request that returns raw bytes (for audio download)."""
    headers = headers or {}
    if isinstance(data, dict):
        data = json.dumps(data).encode()
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — SCRIPT GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

def preprocess_script(script):
    import re
    result = script
    for acronym, expansion in ACRONYM_MAP.items():
        result = re.sub(rf'\b{re.escape(acronym)}\b', expansion, result)
    return result

def generate_script(topic):
    if not ANTHROPIC_API_KEY:
        return preprocess_script(fallback_script(topic))

    persona = AVATAR_PERSONAS.get(topic["avatar"], AVATAR_PERSONAS["arielle"])
    system = (
        f"{persona} "
        f"Company: H&C PRECISE LOGISTICS LLC. Website: hcprelog.com. "
        f"RULES: "
        f"1. Always say 'H&C PRECISE LOGISTICS LLC' — exact name. "
        f"2. NEVER use acronyms. Always say the full words: "
        f"say 'Service-Disabled Veteran-Owned Small Business' not 'SDVOSB', "
        f"say 'Hub Zone' not 'HubZone', "
        f"say 'government contracting' not 'GovCon', "
        f"say 'SAM dot gov' not 'SAM.gov', "
        f"say 'Department of Defense' not 'DoD'. "
        f"3. Speak naturally as if on camera. No stage directions. No asterisks. "
        f"4. Pure spoken words only — no symbols, no slashes, no abbreviations."
    )
    user = (
        f"Write a 30-45 second video script (80-100 words) for an Instagram Reel.\n"
        f"Topic: {topic['title']}\n\n"
        f"Structure:\n"
        f"1. Open with a strong hook (1 sentence)\n"
        f"2. Deliver 2-3 sharp, practical insights (no filler)\n"
        f"3. End with a clear CTA mentioning hcprelog.com\n\n"
        f"Write ONLY the spoken words. No labels. No directions. Natural speech rhythm.\n"
        f"No acronyms. Spell everything out as it would be spoken aloud.\n"
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
        script = preprocess_script(script)
        word_count = len(script.split())
        print(f"[Script] Generated: {word_count} words (~{word_count//2}s speaking time)")
        print(f"[Script] Preview: {script[:120]}...")
        return script
    print(f"[Script] Claude error {status}: {resp}")
    return preprocess_script(fallback_script(topic))

def fallback_script(topic):
    return (
        f"If you're serious about government contracting, here's what most people miss about {topic['title'].lower()}. "
        f"At H&C PRECISE LOGISTICS LLC, we help businesses navigate every step — "
        f"from registration to your first awarded contract. "
        f"Service-Disabled Veteran-Owned Small Business and Hub Zone certified. Based in Durham, North Carolina. "
        f"Start at H C prelog dot com — the free Starter Academy is waiting for you."
    )

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — AUDIO GENERATION (OpenAI TTS primary, edge-tts fallback)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_audio_openai(script, avatar_key):
    """Generate MP3 audio via OpenAI TTS — natural, human-quality voice."""
    voice = OPENAI_VOICES.get(avatar_key, OPENAI_VOICES["arielle"])
    print(f"\n[OpenAI TTS] Generating audio — avatar: {avatar_key}, voice: {voice}")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type":  "application/json",
        "User-Agent":    "HCPreciseLogistics-ReelBot/1.0",
    }
    body = {
        "model":           "tts-1-hd",
        "input":           script,
        "voice":           voice,
        "response_format": "mp3",
    }
    status, audio_bytes = http_binary(
        "POST",
        "https://api.openai.com/v1/audio/speech",
        headers=headers,
        data=body,
        timeout=30,
    )
    if status == 200 and len(audio_bytes) > 1000:
        print(f"[OpenAI TTS] Audio generated: {len(audio_bytes):,} bytes ✓")
        return audio_bytes

    err = audio_bytes.decode(errors="replace")[:200]
    print(f"[OpenAI TTS] Error {status}: {err}")
    print("[OpenAI TTS] → Falling back to edge-tts...")
    return generate_audio_edge_tts(script, avatar_key)

def generate_audio_edge_tts(script, avatar_key):
    """Fallback: Generate MP3 audio via edge-tts (Microsoft Neural TTS — free)."""
    import asyncio
    import edge_tts
    import tempfile

    voice = EDGETTS_VOICES.get(avatar_key, EDGETTS_VOICES["arielle"])
    print(f"\n[edge-tts] Generating audio — avatar: {avatar_key}, voice: {voice}")

    tmp_path = tempfile.mktemp(suffix=".mp3")

    async def _synthesize():
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(tmp_path)

    asyncio.run(_synthesize())

    with open(tmp_path, "rb") as f:
        audio_bytes = f.read()
    os.unlink(tmp_path)

    print(f"[edge-tts] Audio generated: {len(audio_bytes):,} bytes ✓")
    return audio_bytes

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — GITHUB UPLOAD (audio temp file + final video)
# ═══════════════════════════════════════════════════════════════════════════════

def upload_to_github(source, repo_path, is_bytes=False):
    """
    Upload bytes or a local file to the GitHub repo.
    Returns (raw_githubusercontent_url, github_pages_url).
    raw URL is immediately accessible; pages URL needs ~45s CDN propagation.
    """
    raw = source if is_bytes else open(source, "rb").read()
    encoded = base64.b64encode(raw).decode()
    gh_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    status, existing = http("GET", gh_url, headers=headers, timeout=15)
    sha = existing.get("sha") if status == 200 else None

    body = {"message": f"auto: reel {repo_path}", "content": encoded}
    if sha:
        body["sha"] = sha

    size_mb = len(raw) / 1024 / 1024
    print(f"[Upload] Uploading {repo_path} ({size_mb:.1f} MB)...")
    status, resp = http("PUT", gh_url, headers=headers, data=body, timeout=120)

    if status in (200, 201):
        raw_url   = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{repo_path}"
        pages_url = f"https://hcprelog.github.io/public-assets/{repo_path}"
        print(f"[Upload] ✓ {raw_url[:70]}...")
        return raw_url, pages_url

    print(f"[Upload] Failed {status}: {resp}")
    return None, None

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — REPLICATE SADTALKER VIDEO
# ═══════════════════════════════════════════════════════════════════════════════

def _replicate_headers():
    return {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "HCPreciseLogistics-ReelBot/1.0",
    }

def get_sadtalker_version():
    """Fetch the latest SadTalker version ID from Replicate."""
    status, resp = http(
        "GET",
        "https://api.replicate.com/v1/models/cjwbw/sadtalker/versions",
        headers=_replicate_headers(),
        timeout=15,
    )
    if status == 200 and resp.get("results"):
        version = resp["results"][0]["id"]
        print(f"[Replicate] SadTalker version: {version[:16]}...")
        return version
    print(f"[Replicate] Could not fetch SadTalker version: {status} {resp}")
    return None

def create_sadtalker_prediction(avatar_url, audio_url, version):
    """Submit a SadTalker prediction. Returns prediction ID."""
    print(f"\n[Replicate] Submitting SadTalker prediction...")
    print(f"[Replicate] Avatar: {avatar_url[:70]}...")
    print(f"[Replicate] Audio:  {audio_url[:70]}...")

    body = {
        "version": version,
        "input": {
            "source_image":     avatar_url,
            "driven_audio":     audio_url,
            "preprocess":       "full",
            "still_mode":       False,
            "use_enhancer":     True,   # GFPGAN face enhancer for sharper output
            "size_of_image":    512,    # max resolution
            "expression_scale": 1.4,
        },
    }

    status, resp = http(
        "POST", "https://api.replicate.com/v1/predictions",
        headers=_replicate_headers(), data=body, timeout=30,
    )
    if status in (200, 201):
        pred_id = resp["id"]
        print(f"[Replicate] Prediction created: {pred_id} ✓")
        return pred_id

    print(f"[Replicate] Submission failed {status}: {resp}")
    return None

def poll_sadtalker(pred_id, max_wait=600):
    """Poll Replicate until video is ready."""
    print(f"[Replicate] Waiting for render (up to {max_wait//60} min)...")
    start = time.time()
    attempt = 0

    while time.time() - start < max_wait:
        time.sleep(15)
        attempt += 1
        status, resp = http(
            "GET", f"https://api.replicate.com/v1/predictions/{pred_id}",
            headers=_replicate_headers(), timeout=15,
        )

        if status != 200:
            print(f"[Replicate] Poll error {status}: {resp}")
            continue

        pred_status = resp.get("status", "")
        print(f"[Replicate] Status [{attempt}]: {pred_status}")

        if pred_status == "succeeded":
            output = resp.get("output")
            if output:
                video_url = output if isinstance(output, str) else output[0]
                print(f"[Replicate] Video ready: {video_url[:70]}... ✓")
                return video_url
            print("[Replicate] Succeeded but output is empty")
            return None

        if pred_status in ("failed", "canceled"):
            print(f"[Replicate] Prediction {pred_status}: {resp.get('error', 'unknown')}")
            return None

    print(f"[Replicate] Timeout after {max_wait}s")
    return None

def download_video(video_url, tmp_path):
    """Download MP4 from Replicate to a local temp file."""
    print(f"[Video] Downloading from Replicate...")
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
# STEP 5 — INSTAGRAM REEL POST
# ═══════════════════════════════════════════════════════════════════════════════

def generate_reel_caption(topic, avatar_key):
    if not ANTHROPIC_API_KEY:
        return (
            "Watch to the end.\n\n"
            "H&C PRECISE LOGISTICS LLC — GovCon execution support.\n"
            "SDVOSB + HubZone certified.\nhcprelog.com\n\n"
            "#GovCon #SDVOSB #HubZone #FederalContracting #SmallBusiness "
            "#VeteranOwned #HCPreciseLogistics"
        )

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-opus-4-5",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": (
            f"Write a short Instagram Reel caption (max 50 words + 10 hashtags) "
            f"for H&C PRECISE LOGISTICS LLC.\n"
            f"Topic: {topic['title']}\n"
            f"End with: hcprelog.com\n"
            f"Keep it punchy. Start with 'Watch to the end.' or a similar hook."
        )}],
    }
    status, resp = http(
        "POST", "https://api.anthropic.com/v1/messages",
        headers=headers, data=body, timeout=20,
    )
    if status == 200:
        return resp["content"][0]["text"].strip()
    return (
        "Watch to the end.\n\nhcprelog.com\n\n"
        "#GovCon #SDVOSB #HubZone #FederalContracting #HCPreciseLogistics"
    )

def ig_post_reel(video_url, caption):
    """Post video as Instagram Reel via Graph API."""
    print(f"\n[Instagram] Creating Reel container...")

    params = urllib.parse.urlencode({
        "media_type":    "REELS",
        "video_url":     video_url,
        "caption":       caption,
        "share_to_feed": "true",
        "access_token":  INSTAGRAM_ACCESS_TOKEN,
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

    for attempt in range(30):
        time.sleep(8)
        check_url = (
            f"{IG_API_BASE}/{container_id}"
            f"?fields=status_code,status&access_token={INSTAGRAM_ACCESS_TOKEN}"
        )
        _, check = http("GET", check_url, timeout=15)
        status_code = check.get("status_code", "")
        print(f"[Instagram] Container status [{attempt+1}/30]: {status_code}")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            print(f"[Instagram] Processing error: {check}")
            return False

    pub_params = urllib.parse.urlencode({
        "creation_id":  container_id,
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
    print("H&C PRECISE LOGISTICS LLC — Reels Creator (ElevenLabs + Replicate SadTalker)")
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

    # Step 2: Generate audio — OpenAI TTS primary, edge-tts fallback
    audio_bytes = generate_audio_openai(script, avatar_key)
    if not audio_bytes:
        print("FATAL: audio generation failed (both OpenAI TTS and edge-tts)")
        sys.exit(1)

    # Step 3: Upload audio to GitHub — use raw URL (no CDN wait, immediate access)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    audio_repo_path = f"temp/audio_{topic['id']}_{date_str}.mp3"
    audio_raw_url, _ = upload_to_github(audio_bytes, audio_repo_path, is_bytes=True)
    if not audio_raw_url:
        print("FATAL: audio upload to GitHub failed")
        sys.exit(1)

    print("[Wait] Waiting 10s for audio to be accessible via raw URL...")
    time.sleep(10)

    # Step 4: Get SadTalker version and create video
    sadtalker_version = get_sadtalker_version()
    if not sadtalker_version:
        print("FATAL: could not fetch SadTalker version from Replicate")
        sys.exit(1)

    pred_id = create_sadtalker_prediction(avatar_url, audio_raw_url, sadtalker_version)
    if not pred_id:
        print("FATAL: Replicate SadTalker submission failed")
        sys.exit(1)

    replicate_video_url = poll_sadtalker(pred_id)
    if not replicate_video_url:
        print("FATAL: Replicate video render failed or timed out")
        sys.exit(1)

    # Step 5: Download video and upload to GitHub Pages for Instagram
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_video = os.path.join(tmp_dir, "reel.mp4")

        if not download_video(replicate_video_url, tmp_video):
            print("FATAL: could not download video from Replicate")
            sys.exit(1)

        video_repo_path = f"videos/reel_{topic['id']}_{date_str}.mp4"
        _, video_pages_url = upload_to_github(tmp_video, video_repo_path)

    if not video_pages_url:
        print("[Upload] GitHub Pages upload failed — using Replicate URL directly")
        video_pages_url = replicate_video_url

    # Wait for GitHub Pages CDN — Instagram must be able to fetch the URL
    if "github.io" in video_pages_url:
        print("[Wait] Waiting 45s for GitHub Pages CDN...")
        time.sleep(45)

    # Step 6: Generate caption and post to Instagram
    caption = generate_reel_caption(topic, avatar_key)
    success = ig_post_reel(video_pages_url, caption)

    if success:
        print(f"\n✓ Reel posted! Topic: {topic['id']} | Avatar: {avatar_key}")
    else:
        print(f"\n✗ Reel post failed")
        sys.exit(1)

if __name__ == "__main__":
    main()

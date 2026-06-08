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

def get_github_sha(gh_url, headers):
    """Return the SHA of an existing GitHub file, or None if not found."""
    status, resp = http("GET", gh_url, headers=headers, timeout=30)
    sha = resp.get("sha") if status == 200 else None
    print(f"[Upload] GET existing SHA: status={status}, sha={'found' if sha else 'none'}")
    return sha

def upload_to_github(source, repo_path, is_bytes=False):
    """
    Upload bytes or a local file to the GitHub repo.
    Returns (raw_githubusercontent_url, github_pages_url).
    raw URL is immediately accessible; pages URL needs ~45s CDN propagation.
    Handles 422 SHA conflicts by fetching a fresh SHA and retrying once.
    """
    raw = source if is_bytes else open(source, "rb").read()
    encoded = base64.b64encode(raw).decode()
    gh_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    sha = get_github_sha(gh_url, headers)
    body = {"message": f"auto: reel {repo_path}", "content": encoded}
    if sha:
        body["sha"] = sha

    size_mb = len(raw) / 1024 / 1024
    print(f"[Upload] Uploading {repo_path} ({size_mb:.1f} MB)...")
    status, resp = http("PUT", gh_url, headers=headers, data=body, timeout=120)

    # 422 "sha wasn't supplied" = file exists but our GET missed the SHA — retry once
    if status == 422:
        print(f"[Upload] 422 conflict — fetching fresh SHA and retrying...")
        sha2 = get_github_sha(gh_url, headers)
        if sha2:
            body["sha"] = sha2
            status, resp = http("PUT", gh_url, headers=headers, data=body, timeout=120)
            print(f"[Upload] Retry result: {status}")

    if status in (200, 201):
        raw_url   = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{repo_path}"
        pages_url = f"https://hcprelog.github.io/public-assets/{repo_path}"
        print(f"[Upload] ✓ {raw_url[:70]}...")
        return raw_url, pages_url

    print(f"[Upload] Failed {status}: {resp}")
    return None, None

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4A — WAN 2.2 S2V (primary: full-body movement + lip sync)
# Portrait image + audio → natural body/hand/arm movement + lip sync
# Official model — uses /v1/models/{owner}/{name}/predictions (no version hash)
# Falls back to SadTalker if submission or render fails
# ═══════════════════════════════════════════════════════════════════════════════

def create_wan_s2v_prediction(avatar_url, audio_url):
    """
    Submit Wan 2.2 S2V prediction using the official model endpoint.
    Official Replicate models don't have /versions — call the model endpoint directly.
    """
    print(f"\n[Wan S2V] Submitting prediction (full body movement + lip sync)...")
    print(f"[Wan S2V] Avatar: {avatar_url[:70]}...")
    print(f"[Wan S2V] Audio:  {audio_url[:70]}...")
    body = {
        "input": {
            "image": avatar_url,
            "audio": audio_url,
        },
    }
    status, resp = http(
        "POST", "https://api.replicate.com/v1/models/wan-video/wan-2.2-s2v/predictions",
        headers=_replicate_headers(), data=body, timeout=30,
    )
    if status in (200, 201):
        pred_id = resp["id"]
        print(f"[Wan S2V] Prediction created: {pred_id} ✓")
        return pred_id
    print(f"[Wan S2V] Submission failed {status}: {resp}")
    return None

def poll_wan_s2v(pred_id, max_wait=1200):
    """Poll Wan 2.2 S2V until video is ready."""
    print(f"[Wan S2V] Waiting for render (up to {max_wait//60} min)...")
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
            print(f"[Wan S2V] Poll error {status}")
            continue
        pred_status = resp.get("status", "")
        print(f"[Wan S2V] Status [{attempt}]: {pred_status}")
        if pred_status == "succeeded":
            output = resp.get("output")
            if output:
                url = output if isinstance(output, str) else output[0]
                print(f"[Wan S2V] Video ready: {str(url)[:70]}... ✓")
                return url
            print("[Wan S2V] Succeeded but output empty")
            return None
        if pred_status in ("failed", "canceled"):
            print(f"[Wan S2V] {pred_status}: {resp.get('error', 'unknown')}")
            return None
    print(f"[Wan S2V] Timeout after {max_wait}s")
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4B — LATENTSYNC (lip sync enhancement — runs on any video output)
# Replaces robotic mouth movements with precise audio-driven lip sync
# bytedance/latentsync — ~$0.10/run, ~104s, dramatically better sync
# ═══════════════════════════════════════════════════════════════════════════════

def get_latentsync_version():
    """Fetch the latest LatentSync full SHA version hash from Replicate."""
    status, resp = http(
        "GET",
        "https://api.replicate.com/v1/models/bytedance/latentsync/versions",
        headers=_replicate_headers(),
        timeout=15,
    )
    if status == 200 and resp.get("results"):
        version = resp["results"][0]["id"]
        print(f"[LatentSync] Version: {version[:16]}...")
        return version
    print(f"[LatentSync] Could not fetch version: {status} — will skip")
    return None

def run_latentsync(video_url, audio_url):
    """
    Apply LatentSync on top of a talking-head video for much better lip sync.
    Works on both Wan S2V and SadTalker output. Fails silently — raw video
    is used as fallback if LatentSync errors out.
    Version is fetched dynamically to always use the correct full SHA hash.
    """
    print(f"\n[LatentSync] Improving lip sync quality...")
    version = get_latentsync_version()
    if not version:
        return None
    body = {
        "version": version,
        "input": {
            "video": video_url,
            "audio": audio_url,
        },
    }
    status, resp = http(
        "POST", "https://api.replicate.com/v1/predictions",
        headers=_replicate_headers(), data=body, timeout=30,
    )
    if status not in (200, 201):
        print(f"[LatentSync] Submission failed {status}: {resp}")
        return None
    pred_id = resp["id"]
    print(f"[LatentSync] Prediction created: {pred_id} ✓")

    start = time.time()
    attempt = 0
    while time.time() - start < 360:    # 6-min max
        time.sleep(10)
        attempt += 1
        s, r = http(
            "GET", f"https://api.replicate.com/v1/predictions/{pred_id}",
            headers=_replicate_headers(), timeout=15,
        )
        ps = r.get("status", "")
        print(f"[LatentSync] Status [{attempt}]: {ps}")
        if ps == "succeeded":
            out = r.get("output")
            if out:
                url = out if isinstance(out, str) else out[0]
                print(f"[LatentSync] ✓ Enhanced lip sync ready")
                return url
            return None
        if ps in ("failed", "canceled"):
            print(f"[LatentSync] Failed: {r.get('error', 'unknown')}")
            return None
    print(f"[LatentSync] Timeout — using raw video")
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4C — SADTALKER (fallback when Wan S2V is unavailable)
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
            # still_mode=True: head stays neutral, only lips/jaw move.
            # SadTalker's head-pose generation is robotic — disabling it
            # produces a far more natural-looking talking head.
            "still_mode":       True,
            # use_enhancer=False: GFPGAN sharpens each frame independently
            # with no temporal consistency → flickering/glitching between frames.
            # Disabling it gives smoother, more natural motion.
            "use_enhancer":     False,
            "size_of_image":    512,    # max resolution
            # expression_scale=1.0: neutral amplification.
            # 1.4 was over-exaggerating mouth movement — looked unnatural.
            "expression_scale": 1.0,
        },
    }

    for attempt in range(3):
        status, resp = http(
            "POST", "https://api.replicate.com/v1/predictions",
            headers=_replicate_headers(), data=body, timeout=30,
        )
        if status in (200, 201):
            pred_id = resp["id"]
            print(f"[Replicate] Prediction created: {pred_id} ✓")
            return pred_id
        if status == 429:
            retry_after = int(resp.get("retry_after", 15))
            wait = retry_after + 5   # buffer over retry_after
            print(f"[Replicate] Rate limited (429) — waiting {wait}s (attempt {attempt+1}/3)...")
            time.sleep(wait)
            continue
        print(f"[Replicate] Submission failed {status}: {resp}")
        return None
    print("[Replicate] Submission failed after 3 attempts (429 rate limit persistent)")
    return None

def poll_sadtalker(pred_id, max_wait=1200):
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

def process_video_for_instagram(input_path, output_path):
    """
    Re-encode video to Instagram Reels spec: 1080x1920 (9:16), H.264, AAC.
    SadTalker outputs at low resolution with square aspect ratio — Instagram
    Reels requires minimum 1080px wide. FFmpeg is pre-installed on ubuntu-latest.
    """
    import subprocess
    print("[FFmpeg] Converting to Instagram Reels format (1080x1920, 9:16)...")
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", (
            # Scale to fit inside 1080x1920, keep aspect, pad remainder black
            "scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
            "setsar=1"
        ),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",   # high quality (was 23 — lower = sharper, 18 ≈ visually lossless)
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode == 0:
        size = os.path.getsize(output_path)
        print(f"[FFmpeg] Done: {size/1024/1024:.1f} MB ({size:,} bytes) ✓")
        return True
    print(f"[FFmpeg] FFmpeg error:\n{result.stderr[-600:]}")
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
    print("H&C PRECISE LOGISTICS LLC — Reels Creator (Wan S2V + LatentSync + SadTalker)")
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

    # Step 4: Generate talking video
    # Primary: Wan 2.2 S2V — full body movement + lip sync from portrait + audio
    # Fallback: SadTalker — head/face only (proven, reliable)
    # Wan 2.2 S2V (full body movement) is DISABLED — requires paid Replicate credits.
    # It returns 402 Insufficient credit when account balance is below threshold,
    # and the failed attempt still burns the burst rate-limit slot (burst=1 when
    # balance < $5), which causes SadTalker to 429 immediately after.
    # Re-enable when Hunter explicitly approves Wan S2V credit spend.
    wan_used = False
    raw_video_url = None

    print("\n[Video] Generating video via SadTalker (talking head + lip sync)...")
    sadtalker_version = get_sadtalker_version()
    if not sadtalker_version:
        print("FATAL: could not fetch SadTalker version from Replicate")
        sys.exit(1)
    pred_id = create_sadtalker_prediction(avatar_url, audio_raw_url, sadtalker_version)
    if not pred_id:
        print("FATAL: SadTalker submission failed")
        sys.exit(1)
    raw_video_url = poll_sadtalker(pred_id)

    if not raw_video_url:
        print("FATAL: Video render failed (SadTalker)")
        sys.exit(1)

    # Step 4b: LatentSync — improve lip sync quality on top of any video source
    # Works on both Wan S2V and SadTalker output. Fails silently.
    enhanced_url = run_latentsync(raw_video_url, audio_raw_url)
    final_video_url = enhanced_url if enhanced_url else raw_video_url
    print(f"[Video] Source: {'Wan S2V' if wan_used else 'SadTalker'} + "
          f"{'LatentSync enhanced' if enhanced_url else 'raw (LatentSync skipped)'}")

    # Step 5: Download video, convert to Instagram spec, upload to GitHub Pages
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_raw   = os.path.join(tmp_dir, "reel_raw.mp4")
        tmp_final = os.path.join(tmp_dir, "reel_final.mp4")

        if not download_video(final_video_url, tmp_raw):
            print("FATAL: could not download video from Replicate")
            sys.exit(1)

        # Re-encode to Instagram Reels spec (1080x1920, H.264, AAC)
        # SadTalker outputs square/low-res — this ensures Instagram accepts it
        if process_video_for_instagram(tmp_raw, tmp_final):
            upload_video = tmp_final
        else:
            print("[FFmpeg] Conversion failed — uploading raw video as fallback")
            upload_video = tmp_raw

        video_repo_path = f"videos/reel_{topic['id']}_{date_str}.mp4"
        _, video_pages_url = upload_to_github(upload_video, video_repo_path)

    if not video_pages_url:
        print("[Upload] GitHub Pages upload failed — using Replicate URL directly")
        video_pages_url = final_video_url

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

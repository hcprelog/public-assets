"""
H&C PRECISE LOGISTICS LLC — Instagram Reels Creator
Runs weekly (Wednesdays) via instagram-reel.yml
Creates a branded 15-second Reel using:
  - Avatar image (Marcus Hale or Arielle Grant)
  - AI-generated caption/script from Claude
  - FFmpeg for video assembly (pre-installed on GitHub Actions ubuntu runners)
  - Hosts video on GitHub Pages for Instagram Graph API
Posts via Instagram Graph API as a Reel.
"""

import os
import json
import subprocess
import base64
import urllib.request
import urllib.parse
import urllib.error
import time
import sys
import random
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# ── Secrets ───────────────────────────────────────────────────────────────────
INSTAGRAM_USER_ID      = os.environ["INSTAGRAM_USER_ID"]
INSTAGRAM_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
ANTHROPIC_API_KEY      = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY         = os.environ.get("OPENAI_API_KEY", "")
HF_TOKEN               = os.environ.get("HF_TOKEN", "")
GITHUB_TOKEN           = os.environ["GITHUB_TOKEN"]
GITHUB_REPO            = os.environ.get("GITHUB_REPOSITORY", "hcprelog/public-assets")

IG_API_BASE = "https://graph.facebook.com/v25.0"

# ── Avatar image URLs (hosted in this repo via GitHub Pages) ──────────────────
# After uploading avatar images to the repo, update these paths
AVATAR_IMAGES = {
    "marcus":  "https://hcprelog.github.io/public-assets/avatars/Marcus%20Hale.png",
    "arielle": "https://hcprelog.github.io/public-assets/avatars/Arielle%20Grant.png",
}

# Fallback: professional stock images if avatars not yet uploaded
AVATAR_FALLBACK = {
    "marcus":  "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=1080&q=85",
    "arielle": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=1080&q=85",
}

# ── H&C Brand colors ──────────────────────────────────────────────────────────
HC_NAVY  = "0C1F3F"  # hex, no #
HC_WHITE = "FFFFFF"
HC_GOLD  = "C9A84C"

# ── Reels topics (weekly rotation — different from daily posts) ────────────────
REEL_TOPICS = [
    {"id": "r-bid-no-bid",     "avatar": "marcus",  "title": "3 Questions to Ask Before Bidding on Any Contract", "hook": "Stop bidding on contracts you cannot win."},
    {"id": "r-sam-steps",      "avatar": "arielle", "title": "SAM.gov in 5 Steps",                                "hook": "Your first federal contract starts here."},
    {"id": "r-sdvosb-power",   "avatar": "marcus",  "title": "Why SDVOSB Opens Doors Other Certs Don't",          "hook": "SDVOSB is more than a checkbox."},
    {"id": "r-first-contract", "avatar": "arielle", "title": "How to Get Your First Government Contract",         "hook": "Zero federal history? Here is where you start."},
    {"id": "r-cash-flow",      "avatar": "marcus",  "title": "GovCon Cash Flow Secrets",                          "hook": "Government pays well. Just not fast."},
    {"id": "r-capability",     "avatar": "arielle", "title": "Your Capability Statement Checklist",               "hook": "One page. Your entire pitch to a contracting officer."},
    {"id": "r-compliance",     "avatar": "marcus",  "title": "Compliance Matrix Breakdown",                       "hook": "This one document tells COs you are ready."},
    {"id": "r-teaming",        "avatar": "marcus",  "title": "Teaming Your Way Into Bigger Contracts",            "hook": "You don't have to win alone."},
    {"id": "r-hubzone",        "avatar": "arielle", "title": "HubZone: Are You Missing This Certification?",      "hook": "If you're in a HubZone, you have an unfair advantage waiting."},
    {"id": "r-post-award",     "avatar": "marcus",  "title": "Post-Award Pitfalls to Avoid",                      "hook": "Most small businesses fail after the award. Don't be that company."},
]

# ── HTTP helper ───────────────────────────────────────────────────────────────
def http(method, url, headers=None, data=None, timeout=60):
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

# ── GitHub Pages file upload ──────────────────────────────────────────────────
def upload_to_pages(local_path, repo_path, mime_hint="video/mp4"):
    """Upload a local file to GitHub repo → served via GitHub Pages."""
    with open(local_path, "rb") as f:
        raw = f.read()
    encoded  = base64.b64encode(raw).decode()
    gh_url   = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{repo_path}"
    headers  = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    # Check for existing file (need sha to update)
    status, existing = http("GET", gh_url, headers=headers, timeout=15)
    sha = existing.get("sha") if status == 200 else None

    body = {"message": f"auto: reel upload {repo_path}", "content": encoded}
    if sha:
        body["sha"] = sha

    status, resp = http("PUT", gh_url, headers=headers, data=body, timeout=60)
    if status in (200, 201):
        public_url = f"https://hcprelog.github.io/public-assets/{repo_path}"
        print(f"[Upload] {repo_path} → {public_url} ✓")
        return public_url
    print(f"[Upload] Failed {status}: {resp}")
    return None

# ── Download file to temp ─────────────────────────────────────────────────────
def download_file(url, dest_path):
    try:
        urllib.request.urlretrieve(url, dest_path)
        size = Path(dest_path).stat().st_size
        print(f"[Download] {url[:60]}... → {size:,} bytes")
        return True
    except Exception as e:
        print(f"[Download] Failed: {e}")
        return False

# ── Generate background image (DALL-E 3 or fallback) ─────────────────────────
def get_background_image(topic, tmp_dir):
    """Generate or fetch a background image for the reel."""
    bg_path = os.path.join(tmp_dir, "background.jpg")

    # Try DALL-E 3
    if OPENAI_API_KEY:
        prompt = (
            f"Professional, clean corporate background for a government contracting company. "
            f"Abstract geometric shapes in navy blue (#0C1F3F) and white. "
            f"Subtle, elegant, no text. Would work as a video background."
        )
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        body = {"model": "dall-e-3", "prompt": prompt, "n": 1, "size": "1024x1024", "quality": "standard"}
        status, resp = http("POST", "https://api.openai.com/v1/images/generations", headers=headers, data=body, timeout=60)
        if status == 200:
            dalle_url = resp["data"][0]["url"]
            if download_file(dalle_url, bg_path):
                print("[Background] DALL-E 3 background ✓")
                return bg_path

    # Unsplash fallback
    bg_url = "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1080&q=85"
    if download_file(bg_url, bg_path):
        print("[Background] Unsplash background fallback ✓")
        return bg_path

    return None

# ═══════════════════════════════════════════════════════════════════════════════
# ITEM 2 — VIDEO CREATION VIA FFMPEG
# Creates a 15-second Reel:
#   0-3s:   H&C logo intro card (solid navy, white text)
#   3-12s:  Avatar image with animated text overlay (Ken Burns zoom)
#   12-15s: CTA card (hcprelog.com)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_reel_script(topic):
    """Generate 3 text overlays for the reel using Claude."""
    if not ANTHROPIC_API_KEY:
        return {
            "intro": topic["hook"],
            "main": f"{topic['title']}\nH&C PRECISE LOGISTICS LLC",
            "cta": "Start at hcprelog.com\nFree GovCon Starter Academy",
        }

    voice_desc = "Marcus Hale, direct GovCon expert" if topic["avatar"] == "marcus" else "Arielle Grant, business growth advisor"
    system = (
        "You write short, punchy video overlay text for Instagram Reels. "
        "Each line is max 6 words. No punctuation except dashes. All caps for emphasis words only."
    )
    user = (
        f"Write 3 text overlays for a 15-second Instagram Reel.\n"
        f"Topic: {topic['title']}\n"
        f"Hook: {topic['hook']}\n"
        f"Voice: {voice_desc} for H&C PRECISE LOGISTICS LLC\n\n"
        f"Return EXACTLY this JSON (no markdown, no extra text):\n"
        f'{{"intro":"<3-6 word hook>","main":"<2 lines, 6 words each, newline separated>","cta":"<2 lines CTA>"}}'
    )
    headers = {"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    body = {"model": "claude-opus-4-5", "max_tokens": 256, "system": system, "messages": [{"role": "user", "content": user}]}
    status, resp = http("POST", "https://api.anthropic.com/v1/messages", headers=headers, data=body, timeout=20)

    if status == 200:
        try:
            text = resp["content"][0]["text"].strip()
            # Extract JSON even if wrapped in markdown
            import re
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"[Script] JSON parse failed: {e}")

    return {
        "intro": topic["hook"][:40],
        "main": f"{topic['title']}\nH&C PRECISE LOGISTICS LLC",
        "cta": "Learn at hcprelog.com\nFree Starter Academy",
    }

def check_ffmpeg():
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10)
        if result.returncode == 0:
            print("[FFmpeg] Available ✓")
            return True
    except Exception:
        pass
    print("[FFmpeg] Not found — installing...")
    subprocess.run(["apt-get", "install", "-y", "ffmpeg"], capture_output=True)
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10)
        return result.returncode == 0
    except Exception:
        return False

def create_reel_video(topic, avatar_path, bg_path, script, tmp_dir):
    """
    Assemble a 15-second Reel using FFmpeg.
    Output: 1080x1920 MP4 (Instagram Reels format, 9:16).
    """
    output_path = os.path.join(tmp_dir, "reel.mp4")
    avatar_overlay = os.path.join(tmp_dir, "avatar_padded.jpg")

    # ── Sanitize text for FFmpeg drawtext (escape special chars) ─────────────
    def esc(text):
        return text.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")

    intro_text = esc(script["intro"])
    main_lines = script["main"].split("\n")
    main_line1 = esc(main_lines[0]) if main_lines else ""
    main_line2 = esc(main_lines[1]) if len(main_lines) > 1 else ""
    cta_lines  = script["cta"].split("\n")
    cta_line1  = esc(cta_lines[0]) if cta_lines else ""
    cta_line2  = esc(cta_lines[1]) if len(cta_lines) > 1 else ""

    # ── Build FFmpeg filter graph ─────────────────────────────────────────────
    # Segment timing: intro 0-3s | main 3-12s | cta 12-15s
    # Background: scale bg to 1080x1920, Ken Burns zoom
    # Avatar: overlay at center during main segment
    # Text: drawtext with fade in/out

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_regular = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    # Check if font exists, use fallback
    if not os.path.exists(font_path):
        font_path = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        font_regular = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    if not os.path.exists(font_path):
        font_path = "DejaVuSans-Bold.ttf"
        font_regular = "DejaVuSans.ttf"

    filter_complex = (
        # Input 0: background image → 1080x1920, 15 seconds, Ken Burns zoom
        f"[0:v]scale=1920:1920,crop=1080:1920,setsar=1,"
        f"zoompan=z='min(zoom+0.0005,1.05)':d={15*25}:s=1080x1920:fps=25[bg];"

        # Input 1: avatar → scale to 600x600 with rounded feel
        f"[1:v]scale=600:600,setsar=1[avatar];"

        # ── Compose background with avatar overlay (3s to 12s) ──
        f"[bg][avatar]overlay="
        f"x=(W-w)/2:y=(H-h)/2-80:"
        f"enable='between(t,3,12)'[comp];"

        # ── Intro card (0-3s): dark overlay + intro text ──
        f"[comp]drawbox=x=0:y=0:w=1080:h=1920:color=0x0C1F3F@0.85:t=fill:"
        f"enable='lt(t,3)',"

        # Intro text centered
        f"drawtext=fontfile={font_path}:text='{intro_text}':"
        f"fontcolor=white:fontsize=52:x=(w-text_w)/2:y=(h-text_h)/2:"
        f"alpha='if(lt(t,0.5),t/0.5,if(gt(t,2.5),(3-t)/0.5,1))':"
        f"enable='lt(t,3)',"

        # HC brand watermark always visible
        f"drawtext=fontfile={font_path}:text='H&C PRECISE LOGISTICS LLC':"
        f"fontcolor=white@0.7:fontsize=26:x=(w-text_w)/2:y=h-80,"

        # ── Main segment text (3s-12s) ──
        f"drawtext=fontfile={font_path}:text='{main_line1}':"
        f"fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h-280:"
        f"box=1:boxcolor=0x0C1F3F@0.75:boxborderw=12:"
        f"alpha='if(lt(t,3.5),(t-3)/0.5,if(gt(t,11.5),(12-t)/0.5,1))':"
        f"enable='between(t,3,12)',"

        f"drawtext=fontfile={font_regular}:text='{main_line2}':"
        f"fontcolor=white:fontsize=36:x=(w-text_w)/2:y=h-210:"
        f"box=1:boxcolor=0x0C1F3F@0.75:boxborderw=10:"
        f"alpha='if(lt(t,3.5),(t-3)/0.5,if(gt(t,11.5),(12-t)/0.5,1))':"
        f"enable='between(t,3,12)',"

        # ── CTA segment (12s-15s): navy overlay ──
        f"drawbox=x=0:y=0:w=1080:h=1920:color=0x0C1F3F@0.90:t=fill:"
        f"enable='gt(t,12)',"

        f"drawtext=fontfile={font_path}:text='{cta_line1}':"
        f"fontcolor=white:fontsize=54:x=(w-text_w)/2:y=(h-text_h)/2-40:"
        f"alpha='if(lt(t,12.5),(t-12)/0.5,1)':"
        f"enable='gt(t,12)',"

        f"drawtext=fontfile={font_regular}:text='{cta_line2}':"
        f"fontcolor={HC_GOLD}:fontsize=40:x=(w-text_w)/2:y=(h-text_h)/2+40:"
        f"alpha='if(lt(t,12.5),(t-12)/0.5,1)':"
        f"enable='gt(t,12)'"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", "15", "-i", bg_path,      # input 0: background
        "-loop", "1", "-t", "15", "-i", avatar_path,  # input 1: avatar
        "-filter_complex", filter_complex,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-r", "25",
        "-t", "15",
        "-movflags", "+faststart",
        output_path
    ]

    print("[FFmpeg] Rendering reel (this takes ~30s)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        print(f"[FFmpeg] Error:\n{result.stderr[-2000:]}")
        return None

    size = Path(output_path).stat().st_size
    print(f"[FFmpeg] Reel rendered: {size:,} bytes ({size/1024/1024:.1f} MB) ✓")
    return output_path

def ig_post_reel(video_url, caption):
    """Post a Reel to Instagram via Graph API."""
    print(f"\n[Instagram] Creating Reel container...")

    params = urllib.parse.urlencode({
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    })
    url = f"{IG_API_BASE}/{INSTAGRAM_USER_ID}/media"
    status, resp = http("POST", url, data=params.encode(),
                        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)

    if status != 200 or "id" not in resp:
        print(f"[Instagram] Reel container error {status}: {resp}")
        return False

    container_id = resp["id"]
    print(f"[Instagram] Reel container: {container_id} — waiting for processing...")

    # Reels take longer to process (up to 2 min)
    for attempt in range(24):
        time.sleep(10)
        check_url = f"{IG_API_BASE}/{container_id}?fields=status_code,status&access_token={INSTAGRAM_ACCESS_TOKEN}"
        _, check = http("GET", check_url, timeout=15)
        status_code = check.get("status_code", "")
        print(f"[Instagram] Status {attempt+1}/24: {status_code}")
        if status_code == "FINISHED":
            break
        if status_code == "ERROR":
            print(f"[Instagram] Reel processing error: {check}")
            return False

    # Publish
    pub_params = urllib.parse.urlencode({
        "creation_id": container_id,
        "access_token": INSTAGRAM_ACCESS_TOKEN,
    })
    pub_url = f"{IG_API_BASE}/{INSTAGRAM_USER_ID}/media_publish"
    pub_status, pub_resp = http("POST", pub_url, data=pub_params.encode(),
                                headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)

    if pub_status == 200 and "id" in pub_resp:
        print(f"[Instagram] Reel published! Media ID: {pub_resp['id']} ✓")
        return True

    print(f"[Instagram] Publish error {pub_status}: {pub_resp}")
    return False

# ── Caption for the Reel (short, social) ─────────────────────────────────────
def generate_reel_caption(topic):
    if not ANTHROPIC_API_KEY:
        return f"{topic['hook']}\n\n#GovCon #SDVOSB #HubZone #FederalContracting #HCPreciseLogistics\nhcprelog.com"

    headers = {"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    body = {
        "model": "claude-opus-4-5",
        "max_tokens": 300,
        "messages": [{
            "role": "user",
            "content": (
                f"Write a short Instagram Reel caption (max 100 words) for H&C PRECISE LOGISTICS LLC.\n"
                f"Topic: {topic['title']}\n"
                f"Include 10 hashtags and end with: hcprelog.com\n"
                f"Punchy, direct, no fluff."
            )
        }]
    }
    status, resp = http("POST", "https://api.anthropic.com/v1/messages", headers=headers, data=body, timeout=20)
    if status == 200:
        return resp["content"][0]["text"].strip()
    return f"{topic['hook']}\n\n#GovCon #SDVOSB #HubZone #SmallBusiness #VeteranOwned #FederalContracting #HCPreciseLogistics\nhcprelog.com"

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("H&C PRECISE LOGISTICS LLC — Instagram Reels Creator")
    print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    if not check_ffmpeg():
        print("[FFmpeg] FATAL: FFmpeg not available")
        sys.exit(1)

    # Pick topic by week number
    week = datetime.now(timezone.utc).isocalendar()[1]
    topic = REEL_TOPICS[week % len(REEL_TOPICS)]
    print(f"[Topic] {topic['title']} (avatar: {topic['avatar']})")

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Get avatar image
        avatar_url = AVATAR_IMAGES[topic["avatar"]]
        avatar_path = os.path.join(tmp_dir, "avatar.jpg")

        if not download_file(avatar_url, avatar_path):
            # Try fallback
            fallback_url = AVATAR_FALLBACK[topic["avatar"]]
            print(f"[Avatar] Repo image not found, using stock fallback")
            if not download_file(fallback_url, avatar_path):
                print("[Avatar] FATAL: could not download avatar image")
                sys.exit(1)

        # Get background image
        bg_path = get_background_image(topic, tmp_dir)
        if not bg_path:
            print("[Background] FATAL: could not get background image")
            sys.exit(1)

        # Generate script overlays
        script = generate_reel_script(topic)
        print(f"[Script] intro='{script['intro'][:40]}...' | cta='{script['cta'][:30]}...'")

        # Render video
        video_path = create_reel_video(topic, avatar_path, bg_path, script, tmp_dir)
        if not video_path:
            print("[Video] FATAL: FFmpeg render failed")
            sys.exit(1)

        # Upload to GitHub Pages
        date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
        repo_path = f"videos/reel_{topic['id']}_{date_str}.mp4"
        video_url = upload_to_pages(video_path, repo_path)
        if not video_url:
            print("[Upload] FATAL: could not upload video to GitHub Pages")
            sys.exit(1)

        # Wait for GitHub Pages CDN propagation (~30s)
        print("[Wait] Waiting 40s for GitHub Pages to propagate video...")
        time.sleep(40)

        # Generate caption
        caption = generate_reel_caption(topic)

        # Post to Instagram
        success = ig_post_reel(video_url, caption)

        if success:
            print(f"\n✓ Reel posted! Topic: {topic['id']}")
        else:
            print(f"\n✗ Reel posting failed")
            sys.exit(1)

if __name__ == "__main__":
    main()

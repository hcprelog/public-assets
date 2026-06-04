import anthropic
import requests
import os
import random
import time
from datetime import datetime

IG_USER_ID   = os.environ["INSTAGRAM_USER_ID"]
IG_TOKEN     = os.environ["INSTAGRAM_ACCESS_TOKEN"]
OPENAI_KEY   = os.environ.get("OPENAI_API_KEY", "").strip()
HF_TOKEN     = os.environ.get("HF_TOKEN", "").strip()
CUSTOM_TOPIC = os.environ.get("CUSTOM_TOPIC", "").strip()

TOPICS = [
    "federal contract logistics and supply chain excellence",
    "veteran-owned small business success in government contracting",
    "last-mile delivery solutions for federal agencies",
    "SDVOSB set-aside contract opportunities",
    "precision logistics for VA medical supply chains",
    "compliance and reliability in federal transportation",
    "building trust as a small business government contractor",
    "logistics innovation supporting military and federal operations",
    "H&C Precise Logistics mission and values",
    "tips for winning federal logistics contracts",
]

FALLBACK_IMAGES = [
    "https://images.unsplash.com/photo-1601584115197-04ecc0da31d7?w=1080&h=1080&fit=crop",
    "https://images.unsplash.com/photo-1578575437130-527eed3abbec?w=1080&h=1080&fit=crop",
    "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=1080&h=1080&fit=crop",
    "https://images.unsplash.com/photo-1494412651409-8963ce7935a7?w=1080&h=1080&fit=crop",
    "https://images.unsplash.com/photo-1553413077-190dd305871c?w=1080&h=1080&fit=crop",
    "https://images.unsplash.com/photo-1624953587687-daf255b6b80a?w=1080&h=1080&fit=crop",
    "https://images.unsplash.com/photo-1519003722824-194d4455a60c?w=1080&h=1080&fit=crop",
]

topic = CUSTOM_TOPIC if CUSTOM_TOPIC else random.choice(TOPICS)
today = datetime.now().strftime("%A, %B %d, %Y")
print(f"Topic: {topic}")
print(f"Date:  {today}")

IMAGE_PROMPT = f"Professional corporate photography for a federal government logistics company: {topic}. Dark navy and gold color scheme, clean modern executive aesthetic, photorealistic, no text in image, 4K quality, cinematic lighting."

# ── Step 1: Caption via Claude ──────────────────────────────
client = anthropic.Anthropic()
msg = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=500,
    messages=[{"role": "user", "content": f"""You are the social media voice for H&C Precise Logistics LLC, a Service-Disabled Veteran-Owned Small Business (SDVOSB) specializing in federal government logistics, last-mile delivery, and supply chain solutions.

Write an Instagram caption for today ({today}) on this topic: {topic}

Requirements:
- Professional, confident, and mission-driven tone
- 3-5 sentences max
- Include 1 relevant call to action
- End with 8-12 relevant hashtags including #SDVOSB #FederalContracting #HCPreciseLogistics #GovCon
- No excessive emojis — keep it sharp and credible
- Write only the caption, nothing else."""}]
)
caption = msg.content[0].text.strip()
print(f"\nCaption:\n{caption}\n")

# ── Step 2: Image — priority: DALL-E 3 → FLUX.1 → Unsplash ─
image_url = None

# Option A: DALL-E 3 (requires platform.openai.com billing)
if OPENAI_KEY:
    print("Trying DALL-E 3...")
    try:
        dalle_resp = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"},
            json={"model": "dall-e-3", "prompt": IMAGE_PROMPT, "n": 1, "size": "1024x1024", "quality": "standard"},
            timeout=60
        )
        dalle_data = dalle_resp.json()
        if "data" in dalle_data:
            image_url = dalle_data["data"][0]["url"]
            print(f"DALL-E 3 image ready")
        else:
            print(f"DALL-E 3 unavailable: {dalle_data.get('error',{}).get('message','unknown')} — trying FLUX.1")
    except Exception as e:
        print(f"DALL-E 3 error: {e} — trying FLUX.1")

# Option B: FLUX.1-schnell via Hugging Face (free, high quality)
if not image_url:
    print("Trying FLUX.1-schnell (Hugging Face)...")
    try:
        hf_headers = {"Content-Type": "application/json"}
        if HF_TOKEN:
            hf_headers["Authorization"] = f"Bearer {HF_TOKEN}"
        hf_resp = requests.post(
            "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell",
            headers=hf_headers,
            json={"inputs": IMAGE_PROMPT, "parameters": {"width": 1024, "height": 1024}},
            timeout=60
        )
        if hf_resp.status_code == 200 and "image" in hf_resp.headers.get("content-type", ""):
            # Upload image bytes to GitHub as temp asset, use raw URL for Instagram
            import base64
            img_b64 = base64.b64encode(hf_resp.content).decode()
            ts = int(time.time())
            gh_token = os.environ.get("GITHUB_TOKEN", "")
            if gh_token:
                upload = requests.put(
                    f"https://api.github.com/repos/hcprelog/public-assets/contents/automation/temp_img_{ts}.jpg",
                    headers={"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"},
                    json={"message": f"Temp image {ts}", "content": img_b64}
                )
                if upload.status_code in (201, 200):
                    image_url = f"https://raw.githubusercontent.com/hcprelog/public-assets/main/automation/temp_img_{ts}.jpg"
                    print(f"FLUX.1 image uploaded and ready")
                else:
                    print(f"FLUX.1 upload failed: {upload.status_code} — falling back to Unsplash")
            else:
                print("No GITHUB_TOKEN for upload — falling back to Unsplash")
        else:
            print(f"FLUX.1 returned HTTP {hf_resp.status_code} — falling back to Unsplash")
    except Exception as e:
        print(f"FLUX.1 error: {e} — falling back to Unsplash")

# Option C: Curated Unsplash (always works)
if not image_url:
    print("Using curated Unsplash image")
    image_url = FALLBACK_IMAGES[datetime.now().weekday() % len(FALLBACK_IMAGES)]
    print(f"Image: {image_url}")

# Verify image accessible
img_check = requests.get(image_url, timeout=30)
if img_check.status_code != 200:
    raise Exception(f"Image URL returned HTTP {img_check.status_code}")
print(f"Image verified ({len(img_check.content):,} bytes)")

# ── Step 3: Create Instagram container ─────────────────────
print("\nCreating Instagram media container...")
container_resp = requests.post(
    f"https://graph.facebook.com/v25.0/{IG_USER_ID}/media",
    data={"image_url": image_url, "caption": caption, "access_token": IG_TOKEN}
)
container_data = container_resp.json()
print(f"Container response: {container_data}")
if "id" not in container_data:
    raise Exception(f"Container creation failed: {container_data}")
container_id = container_data["id"]

# ── Step 4: Wait for FINISHED ───────────────────────────────
print("Waiting for container to process...")
for attempt in range(12):
    time.sleep(5)
    status = requests.get(
        f"https://graph.facebook.com/v25.0/{container_id}",
        params={"fields": "status_code", "access_token": IG_TOKEN}
    ).json().get("status_code", "")
    print(f"  [{attempt+1}] status = {status}")
    if status == "FINISHED":
        break
    if status == "ERROR":
        raise Exception("Container processing ERROR")
else:
    raise Exception("Container never reached FINISHED")

# ── Step 5: Publish ─────────────────────────────────────────
print("\nPublishing...")
pub_resp = requests.post(
    f"https://graph.facebook.com/v25.0/{IG_USER_ID}/media_publish",
    data={"creation_id": container_id, "access_token": IG_TOKEN}
)
pub_data = pub_resp.json()
print(f"Publish response: {pub_data}")
if "id" not in pub_data:
    raise Exception(f"Publish failed: {pub_data}")

print(f"\n✅ SUCCESS")
print(f"Post ID: {pub_data['id']}")
print(f"Account: @hc_precise_logistics")
print(f"Topic: {topic}")

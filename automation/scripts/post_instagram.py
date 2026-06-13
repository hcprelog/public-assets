import os
import json
import requests
from openai import OpenAI
import anthropic
from datetime import datetime, timezone
from pathlib import Path

INSTAGRAM_USER_ID = os.environ["INSTAGRAM_USER_ID"]
INSTAGRAM_ACCESS_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

QUEUE_FILE = Path(__file__).parent / "instagram_queue.json"
GRAPH_API = "https://graph.facebook.com/v25.0"

ROTATING_THEMES = [
    {"theme": "SDVOSB certification — what it means and why it matters", "image_style": "Bold navy blue graphic, white bold text 'SDVOSB CERTIFIED', green accent bar, Montserrat font, federal contractor branding"},
    {"theme": "HUBZone program — how underserved communities get federal contracts", "image_style": "Clean infographic, white background, navy blue headers, green icons, professional minimal design"},
    {"theme": "VA contract success — how H&C serves veterans who served us", "image_style": "Cinematic medical courier van driving toward VA hospital at sunrise, warm golden light, photorealistic"},
    {"theme": "How federal subcontracting revenue works — the Net 30 model", "image_style": "Bold flat design flow chart, navy background, white boxes with green borders, arrow diagram, Montserrat font"},
    {"theme": "GovCon tips for veteran entrepreneurs — getting started", "image_style": "Professional executive portrait style, navy blue background, bold white quote text, green underline accent"},
    {"theme": "PRIME READY consulting plan — teaming access for small businesses", "image_style": "Split design, left navy with white 'PRIME READY', right white with green checkmarks, SaaS marketing style"},
    {"theme": "SAM.gov registration — first step to federal contracting", "image_style": "Clean credential display, white background, navy bold text, green label tags, official certificate aesthetic"},
    {"theme": "Federal set-aside contracts — who qualifies and how to win", "image_style": "Bold infographic, navy background, white text, green accent icons, modern federal contractor branding"},
]


def load_queue():
    with open(QUEUE_FILE) as f:
        return json.load(f)


def save_queue(queue):
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def get_next_post(queue):
    for post in queue["posts"]:
        if post["status"] == "pending":
            return post
    return None


def generate_caption_with_claude(theme):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": f"""Write an Instagram caption for H&C Precise Logistics LLC.

Company: H&C Precise Logistics LLC (@hc_precise_logistics)
President: Dennis Hunter — 20+ years military service
Certifications: SDVOSB (Service-Disabled Veteran-Owned) + HUBZone
What we do: Federal government contracting, VA medical courier contracts, GovCon consulting
Location: Durham, NC | Website: hcprelog.com
Brand voice: Professional, authoritative, mission-driven, veteran pride

Post theme: {theme}

Write a caption with:
- Strong hook as the first line (no fluff)
- 3-4 short punchy paragraphs
- Clear call to action pointing to hcprelog.com or DM
- 8-10 relevant hashtags on the last line

Include hashtags from: #SDVOSB #VeteranOwnedBusiness #HUBZone #FederalContracting #GovCon #VeteranBusiness #DurhamNC #SmallBusiness #GovernmentContracts #VeteranEntrepreneur

Return only the caption text, nothing else."""
        }]
    )
    return message.content[0].text.strip()


def generate_image(prompt):
    client = OpenAI(api_key=OPENAI_API_KEY)
    full_prompt = (
        f"{prompt}. Brand colors: deep navy blue #0033A0 and green #00B140. "
        "Font: Montserrat bold. Square 1:1 format. Professional federal contractor aesthetic. "
        "No clipart. Clean, modern, high quality."
    )
    response = client.images.generate(
        model="dall-e-3",
        prompt=full_prompt,
        size="1024x1024",
        quality="hd",
        n=1,
    )
    return response.data[0].url


def create_media_container(image_url, caption):
    response = requests.post(
        f"{GRAPH_API}/{INSTAGRAM_USER_ID}/media",
        data={
            "image_url": image_url,
            "caption": caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        }
    )
    response.raise_for_status()
    return response.json()["id"]


def publish_media(creation_id):
    response = requests.post(
        f"{GRAPH_API}/{INSTAGRAM_USER_ID}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        }
    )
    response.raise_for_status()
    return response.json()["id"]


def get_rotating_theme(queue):
    posted_count = sum(1 for p in queue["posts"] if p["status"] == "posted")
    return ROTATING_THEMES[posted_count % len(ROTATING_THEMES)]


def main():
    queue = load_queue()
    post = get_next_post(queue)

    if post:
        print(f"Using queued post: {post['theme']}")
        caption = post["caption"]
        image_prompt = post["image_prompt"]
    else:
        theme_data = get_rotating_theme(queue)
        print(f"Queue empty — generating with Claude: {theme_data['theme']}")
        caption = generate_caption_with_claude(theme_data["theme"])
        image_prompt = theme_data["image_style"]

    print("Generating image with DALL-E 3...")
    image_url = generate_image(image_prompt)
    print(f"Image URL: {image_url[:80]}...")

    print("Creating Instagram media container...")
    creation_id = create_media_container(image_url, caption)

    print("Publishing...")
    post_id = publish_media(creation_id)

    now = datetime.now(timezone.utc).isoformat()
    print(f"Published! Instagram Post ID: {post_id} at {now}")

    if post:
        post["status"] = "posted"
        post["posted_at"] = now
        post["instagram_post_id"] = post_id
    else:
        queue["posts"].append({
            "theme": theme_data["theme"],
            "caption": caption,
            "image_prompt": image_prompt,
            "status": "posted",
            "posted_at": now,
            "instagram_post_id": post_id,
        })

    save_queue(queue)
    print("Queue saved.")


if __name__ == "__main__":
    main()

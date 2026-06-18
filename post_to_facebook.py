"""
AI ছবি জেনারেট করে স্বয়ংক্রিয়ভাবে Facebook Page-এ পোস্ট করার স্ক্রিপ্ট।
GitHub Actions থেকে নির্ধারিত সময়ে (cron) এই স্ক্রিপ্ট চলবে।

প্রতিবার রান হলে এই স্ক্রিপ্ট:
  1. নির্ধারিত টপিক লিস্ট থেকে র্যান্ডমলি একটা নতুন ছবির prompt বানায়
  2. সেই prompt দিয়ে ছবি জেনারেট করে (Pollinations AI)
  3. AI দিয়ে একটা বাংলা caption লিখে দেয়
  4. ছবি + caption Facebook Page-এ পোস্ট করে দেয়

প্রয়োজনীয় Environment Variables (GitHub Secrets থেকে আসে):
  FB_PAGE_TOKEN  - Facebook Page Access Token (long-lived হওয়া আবশ্যক)
  FB_PAGE_ID     - Facebook Page ID
  STYLE          - (ঐচ্ছিক) যেমন "photorealistic, DSLR photography, 8k resolution"
"""

import os
import random
import sys
import urllib.parse

import requests

POLLINATIONS_TEXT_URL = "https://text.pollinations.ai/"
POLLINATIONS_IMAGE_URL = "https://image.pollinations.ai/prompt/"
FB_GRAPH_API = "https://graph.facebook.com/v21.0"

ANGLE_HINTS = [
    "from an unusual or creative camera angle",
    "with dramatic, moody lighting",
    "in a candid, everyday moment",
    "with a unique and vivid color palette",
    "with an interesting, well-balanced composition",
    "showing fine detail and texture up close",
    "during golden hour with warm light",
    "with a cinematic, atmospheric mood",
    "from a wide establishing shot perspective",
    "with a minimalist, clean aesthetic",
]

# 📝 আপনার পছন্দের ঐতিহাসিক টপিকগুলোর লিস্ট (এখানে ইচ্ছেমতো আরও বাড়াতে পারবেন)
HISTORICAL_TOPICS = [
    "Historical Place in the World",
    "Ancient Wonders of the World",
    "Mysterious Lost Cities in History",
    "Medieval Castles and Fortresses",
    "Ancient Roman and Greek Architecture",
    "UNESCO World Heritage Sites",
    "Ancient Egyptian Temples and Pharaoh Heritage",
    "Mughal Architecture and Historic Forts",
    "Legendary Mythological Kingdoms",
    "Ancient European Gothic Cathedrals"
]


def generate_prompt(topic: str, style: str) -> str:
    """টপিক থেকে AI দিয়ে একটা নতুন, ভিন্নধর্মী ছবির prompt বানায়।"""
    hint = random.choice(ANGLE_HINTS)
    instruction = (
        "You generate image-generation prompts. Output exactly ONE creative, "
        "highly specific, detailed English image-generation prompt related to "
        f'the topic "{topic}", {hint}. Make it specific and different from a '
        "generic stock-photo description. Output ONLY the prompt text itself, "
        "nothing else, no quotes, no numbering, no extra commentary."
    )
    url = POLLINATIONS_TEXT_URL + urllib.parse.quote(instruction)
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    prompt = resp.text.strip()
    if not prompt:
        raise RuntimeError("AI prompt তৈরি করতে ব্যর্থ হয়েছে (খালি উত্তর এসেছে)")
    if style:
        prompt = f"{prompt}, {style}"
    return prompt


def generate_caption(prompt_text: str) -> str:
    """ছবির prompt থেকে একটা বাংলা Facebook caption বানায়। ব্যর্থ হলে ডিফল্ট caption দেয়।"""
    instruction = (
        "Write exactly one short, catchy Facebook caption in Bengali (with 1-2 "
        f'relevant emojis) for an AI-generated image described as: "{prompt_text}". '
        "Output only the caption text, nothing else, no quotation marks."
    )
    try:
        url = POLLINATIONS_TEXT_URL + urllib.parse.quote(instruction)
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        caption = resp.text.strip()
        return caption or "✨ AI ছবি"
    except Exception:
        return "✨ AI ছবি"


def generate_image(prompt_text: str) -> bytes:
    """prompt থেকে ছবি জেনারেট করে এবং raw bytes রিটার্ন করে।"""
    seed = random.randint(0, 999999)
    query = urllib.parse.quote(prompt_text)
    url = f"{POLLINATIONS_IMAGE_URL}{query}?width=1024&height=1024&model=flux&seed={seed}"
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return resp.content


def post_to_facebook(image_bytes: bytes, caption: str, token: str, page_id: str):
    """ছবি Facebook Page-এ পোস্ট করে। (success, post_id_or_error_message) রিটার্ন করে।"""
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    data = {"message": caption or "✨ AI ছবি", "access_token": token}
    resp = requests.post(url, data=data, files=files, timeout=60)
    result = resp.json()
    if "id" in result:
        return True, result["id"]
    error_msg = result.get("error", {}).get("message", "অজানা সমস্যা / ভুল Token বা Page ID")
    return False, error_msg


def main():
    style = os.environ.get("STYLE", "").strip()
    fb_token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    fb_page_id = os.environ.get("FB_PAGE_ID", "").strip()

    if not fb_token or not fb_page_id:
        print("❌ FB_PAGE_TOKEN বা FB_PAGE_ID সেট করা নেই। GitHub Secrets চেক করুন।")
        sys.exit(1)

    # 🎲 লিস্ট থেকে প্রতিবার র্যান্ডমলি ১টি টপিক সিলেক্ট করা হচ্ছে
    topic = random.choice(HISTORICAL_TOPICS)
    print(f"🏷️  আজকের নির্বাচিত টপিক: {topic}")

    print("🤖 AI দিয়ে নতুন prompt বানানো হচ্ছে...")
    prompt = generate_prompt(topic, style)
    print(f"   প্রম্পট: {prompt}")

    print("📝 AI দিয়ে caption লেখা হচ্ছে...")
    caption = generate_caption(prompt)
    print(f"   ক্যাপশন: {caption}")

    print("🎨 ছবি জেনারেট হচ্ছে...")
    image_bytes = generate_image(prompt)
    print(f"   ছবি তৈরি হয়েছে ({len(image_bytes)} bytes)")

    print("📘 Facebook-এ পোস্ট হচ্ছে...")
    success, result = post_to_facebook(image_bytes, caption, fb_token, fb_page_id)

    if success:
        print(f"✅ পোস্ট সফল হয়েছে! Post ID: {result}")
    else:
        print(f"❌ পোস্ট ব্যর্থ হয়েছে: {result}")
        sys.exit(1)


if __name__ == "__main__":
    main()

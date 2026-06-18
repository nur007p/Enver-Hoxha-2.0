"""
Hugging Face Hub API ব্যবহার করে AI ছবি জেনারেট ও Facebook Page-এ অটো-পোস্ট করার স্ক্রিপ্ট।
"""

import os
import random
import sys
import time
import urllib.parse
import requests
from huggingface_hub import InferenceClient

POLLINATIONS_TEXT_URL = "https://text.pollinations.ai/"
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
    "Ancient European Gothic Cathedrals",
    "If Ancient Civilizations Never Died",
]

def safe_text_request(url: str, max_retries: int = 3, delay: int = 5) -> requests.Response:
    """টেক্সট/ক্যাপশন জেনারেটরের জন্য রিট্রাই মেকানিজম।"""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=90)
            resp.raise_for_status()
            return resp
        except Exception as e:
            print(f"⚠️ টেক্সট সার্ভার এরর (চেষ্টা {attempt + 1}): {e}. আবার চেষ্টা করা হচ্ছে...")
            if attempt < max_retries - 1:
                time.sleep(delay)
            else:
                raise e

def generate_prompt(topic: str, style: str) -> str:
    """টপিক থেকে AI দিয়ে একটা নতুন ছবির prompt বানায়।"""
    hint = random.choice(ANGLE_HINTS)
    instruction = (
        "You generate image-generation prompts. Output exactly ONE creative, "
        "highly specific, detailed English image-generation prompt related to "
        f'the topic "{topic}", {hint}. Output ONLY the prompt text itself, '
        "nothing else, no quotes, no numbering."
    )
    url = POLLINATIONS_TEXT_URL + urllib.parse.quote(instruction)
    resp = safe_text_request(url)
    prompt = resp.text.strip()
    if not prompt:
        raise RuntimeError("AI prompt তৈরি করতে ব্যর্থ হয়েছে")
    if style:
        prompt = f"{prompt}, {style}"
    return prompt

def generate_caption(prompt_text: str) -> str:
    """ছবির prompt থেকে একটা বাংলা Facebook caption বানায়।"""
    instruction = (
        "Write exactly one short, catchy Facebook caption in Bengali (with 1-2 "
        f'relevant emojis) for an AI-generated image described as: "{prompt_text}". '
        "Output only the caption text, nothing else."
    )
    try:
        url = POLLINATIONS_TEXT_URL + urllib.parse.quote(instruction)
        resp = safe_text_request(url, max_retries=2, delay=3)
        return resp.text.strip() or "✨ AI ছবি"
    except Exception:
        return "✨ AI ছবি"

def generate_image_hf_official(prompt_text: str, hf_token: str) -> bytes:
    """Hugging Face Hub লাইব্রেরি ব্যবহার করে সুরক্ষিত উপায়ে ছবি জেনারেট করে।"""
    print("🎨 Hugging Face অফিসিয়াল ক্লায়েন্ট দিয়ে ছবি জেনারেট করা হচ্ছে...")
    
    # ক্লায়েন্ট ইনিশিয়েলাইজেশন
    client = InferenceClient(token=hf_token)
    
    for attempt in range(3):
        try:
            # FLUX.1-schnell মডেল ব্যবহার করে ইমেজ জেনারেশন
            image = client.text_to_image(
                prompt_text, 
                model="black-forest-labs/FLUX.1-schnell"
            )
            
            # ইমেজ অবজেক্টকে raw bytes-এ কনভার্ট করা হচ্ছে ফেসবুক পোস্টের জন্য
            import io
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            return img_byte_arr.getvalue()
            
        except Exception as e:
            print(f"⚠️ ছবি জেনারেশন ব্যর্থ (চেষ্টা {attempt + 1}): {e}")
            if "503" in str(e) or "Loading" in str(e):
                print("⏳ মডেল লোড হতে সময় নিচ্ছে... ২০ সেকেন্ড অপেক্ষা করা হচ্ছে...")
                time.sleep(20)
            elif attempt < 2:
                time.sleep(10)
            else:
                raise e
    raise RuntimeError("Hugging Face ক্লায়েন্ট থেকে ছবি জেনারেট করা সম্ভব হয়নি।")

def post_to_facebook(image_bytes: bytes, caption: str, token: str, page_id: str):
    """ছবি Facebook Page-এ পোস্ট করে।"""
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    data = {"message": caption, "access_token": token}
    
    resp = requests.post(url, data=data, files=files, timeout=90)
    result = resp.json()
    if "id" in result:
        return True, result["id"]
    return False, result.get("error", {}).get("message", "অজানা ফেসবুক এরর")

def main():
    style = os.environ.get("STYLE", "").strip()
    fb_token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    fb_page_id = os.environ.get("FB_PAGE_ID", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()

    if not fb_token or not fb_page_id or not hf_token:
        print("❌ প্রোজেক্টের প্রয়েজনীয় টোকেনগুলো (FB বা HF) সেট করা নেই। GitHub Secrets চেক করুন।")
        sys.exit(1)

    topic = random.choice(HISTORICAL_TOPICS)
    print(f"🏷️  নির্বাচিত টপিক: {topic}")

    prompt = generate_prompt(topic, style)
    print(f"🚀 প্রম্পট রেডি: {prompt}")

    caption = generate_caption(prompt)
    print(f"📝 ক্যাপশন রেডি: {caption}")

    image_bytes = generate_image_hf_official(prompt, hf_token)
    print(f"✅ ছবি সফলভাবে জেনারেট হয়েছে ({len(image_bytes)} bytes)")

    print("📘 Facebook-এ পোস্ট করা হচ্ছে...")
    success, result = post_to_facebook(image_bytes, caption, fb_token, fb_page_id)

    if success:
        print(f"✅ ফেসবুক পোস্ট সফল! Post ID: {result}")
    else:
        print(f"❌ ফেসবুক পোস্ট ব্যর্থ: {result}")
        sys.exit(1)

if __name__ == "__main__":
    main()

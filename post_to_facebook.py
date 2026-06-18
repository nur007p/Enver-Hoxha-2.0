"""
Hugging Face Hub API ব্যবহার করে সম্পূর্ণ অটোমেটিক ফেসবুক পোস্ট স্ক্রিপ্ট।
ফিডব্যাক অনুযায়ী জাপানি ক্যারেক্টার বাগ ফিক্সড এবং এপিআই স্টেবিলিটি নিশ্চিত করা হয়েছে।
"""

import os
import random
import sys
import time
import io
import requests
from huggingface_hub import InferenceClient

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

def get_hf_text(client: InferenceClient, instruction: str, max_tokens: int = 150) -> str:
    """Hugging Face-এর শক্তিশালী লার্জ ল্যাঙ্গুয়েজ মডেল ব্যবহার করে টেক্সট জেনারেট করার সেফ ফাংশন।"""
    text_model = "Qwen/Qwen2.5-72B-Instruct"
    
    for attempt in range(3):
        try:
            messages = [{"role": "user", "content": instruction}]
            response = client.chat_completion(
                model=text_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            result = response.choices[0].message.content
            if result:
                return result.strip()
        except Exception as e:
            print(f"⚠️ HF টেক্সট মডেল এরর (চেষ্টা {attempt + 1}): {e}")
            time.sleep(10)
    raise RuntimeError("Hugging Face টেক্সট সার্ভার থেকে রেসপন্স পাওয়া যায়নি।")

def auto_generate_topic(client: InferenceClient) -> str:
    """Hugging Face AI ব্যবহার করে নিজে থেকে একটি নতুন এবং অনন্য টপিক তৈরি করে।"""
    # জাপানি ক্যারেক্টার বাগটি ফিক্স করা হলো (アイデア -> আইডিয়া)
    print("🔍 Hugging Face AI-এর কাছ থেকে নতুন ইউনিক টপিক আইডিয়া নেওয়া হচ্ছে...")
    
    categories = [
        "Ancient Lost Civilization", "Mysterious Historical Event", 
        "Architectural Wonder of the Past", "Mythological Kingdom", 
        "Medieval Secret Castle", "Historical Underwater Ruins",
        "Futuristic Cyberpunk Cityscape", "Deep Space Exploration Wonder",
        "Surreal Steampunk Laboratory", "Nature-infused Fantasy Village"
    ]
    chosen_cat = random.choice(categories)
    
    instruction = (
        f"Give me exactly one interesting, specific, and unique image idea/topic about a '{chosen_cat}'. "
        "It should be suitable for creating a stunning visual. Output ONLY the topic name in one short sentence, "
        "no quotes, no intro, no explanation."
    )
    
    topic = get_hf_text(client, instruction, max_tokens=50)
    return topic or "Mysterious Ancient Civilization"

def generate_prompt(client: InferenceClient, topic: str, style: str) -> str:
    """টপিক থেকে AI দিয়ে একটি চমৎকার ছবির prompt বানায়।"""
    print("🚀 প্রম্পট টেক্সট জেনারেট করা হচ্ছে...")
    hint = random.choice(ANGLE_HINTS)
    instruction = (
        "You generate image-generation prompts. Output exactly ONE creative, "
        "highly specific, detailed English image-generation prompt related to "
        f'the topic "{topic}", {hint}. Output ONLY the prompt text itself, '
        "nothing else, no quotes, no numbering."
    )
    prompt = get_hf_text(client, instruction, max_tokens=150)
    if not prompt:
        raise RuntimeError("AI prompt তৈরি করতে ব্যর্থ হয়েছে")
    if style:
        prompt = f"{prompt}, {style}"
    return prompt

def generate_caption(client: InferenceClient, prompt_text: str) -> str:
    """ছবির prompt থেকে একটা বাংলা Facebook caption এবং প্রাসঙ্গিক হ্যাশট্যাগ বানায়।"""
    print("📝 বাংলা ক্যাপশন ও হ্যাশট্যাগ তৈরি করা হচ্ছে...")
    instruction = (
        "Write exactly one short, catchy Facebook caption in Bengali (with 1-2 "
        f'relevant emojis like 📜, 🏛️, 🎨, 🌌) for an AI-generated image described as: "{prompt_text}". '
        "Also include 3-4 relevant English hashtags at the very end (e.g., #AIArt #MidjourneyStyle). "
        "Output only the caption text and hashtags, nothing else. Do not use sparkle symbols like ✨."
    )
    try:
        caption = get_hf_text(client, instruction, max_tokens=150)
        caption = caption.replace("✨", "📜").replace("❇️", "🏛️").strip('"').strip("'")
        return caption or "ইতিহাস আর কল্পনার পাতা থেকে এক রহস্যময় ঝলক... 📜🎨\n\n#AIArt #DigitalArt"
    except Exception:
        return "ইতিহাস আর কল্পনার পাতা থেকে এক রহস্যময় ঝলক... 📜🎨\n\n#AIArt #DigitalArt"

def generate_image_hf_official(client: InferenceClient, prompt_text: str) -> bytes:
    """Hugging Face Hub লাইব্রেরি ব্যবহার করে FLUX ছবি জেনারেট করে।"""
    print("🎨 Hugging Face FLUX মডেল দিয়ে ছবি জেনারেট করা হচ্ছে...")
    
    for attempt in range(3):
        try:
            # ফ্রি ইনফারেন্স এন্ডপয়েন্টে এরর এড়াতে কাস্টম রেজোলিউশন ডিফল্ট রাখা হলো (প্রয়োজনে PIL দিয়ে রিসাইজ করা যাবে)
            image = client.text_to_image(
                prompt_text, 
                model="black-forest-labs/FLUX.1-schnell"
            )
            
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            return img_byte_arr.getvalue()
            
        except Exception as e:
            print(f"⚠️ ছবি জেনারেশন ব্যর্থ (চেষ্টা {attempt + 1}): {e}")
            if "503" in str(e) or "Loading" in str(e):
                print("⏳ মডেল লোড হতে সময় নিচ্ছে... ২০ সেকেন্ড অপেক্ষা করা হচ্ছে...")
                time.sleep(20)
            elif attempt < 2:
                time.sleep(10)
            else:
                raise e
    raise RuntimeError("Hugging Face ক্লায়েন্ট থেকে ছবি জেনারেট করা সম্ভব হয়নি।")

def post_to_facebook(image_bytes: bytes, caption: str, token: str, page_id: str):
    """ছবি Facebook Page-এ পোস্ট করে (নিরাপদ এরর হ্যান্ডলিং সহ)।"""
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    data = {"message": caption, "access_token": token}
    
    try:
        resp = requests.post(url, data=data, files=files, timeout=90)
        result = resp.json()
        if "id" in result:
            return True, result["id"]
        return False, result.get("error", {}).get("message", "অজানা ফেসবুক এরর")
    except Exception as network_error:
        return False, f"ফেসবুক সার্ভার কানেকশন এরর: {network_error}"

def main():
    style = os.environ.get("STYLE", "").strip()
    fb_token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    fb_page_id = os.environ.get("FB_PAGE_ID", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()

    if not fb_token or not fb_page_id or not hf_token:
        print("❌ প্রোজেক্টের প্রয়েজনীয় টোকেনগুলো (FB বা HF) সেট করা নেই। GitHub Secrets চেক করুন।")
        sys.exit(1)

    client = InferenceClient(token=hf_token)

    # ১. টপিক জেনারেট করা
    topic = auto_generate_topic(client)
    print(f"🏷️  AI জেনারেটেড নতুন টপিক: {topic}")

    # ২. প্রম্পট জেনারেট করা
    prompt = generate_prompt(client, topic, style)
    print(f"🚀 প্রম্পট রেডি: {prompt}")

    # ৩. ক্যাপশন জেনারেট করা
    caption = generate_caption(client, prompt)
    print(f"📝 ক্যাপশন রেডি:\n{caption}")

    # ৪. ইমেজ জেনারেশন
    image_bytes = generate_image_hf_official(client, prompt)
    print(f"✅ ছবি সফলভাবে জেনারেট হয়েছে ({len(image_bytes)} bytes)")

    # ৫. ফেসবুকে পোস্ট
    print("📘 Facebook-এ পোস্ট করা হচ্ছে...")
    success, result = post_to_facebook(image_bytes, caption, fb_token, fb_page_id)

    if success:
        print(f"✅ ফেসবুক পোস্ট সফল! Post ID: {result}")
    else:
        print(f"❌ ফেসবুক পোস্ট ব্যর্থ: {result}")
        sys.exit(1)

if __name__ == "__main__":
    main()

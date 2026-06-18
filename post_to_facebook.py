"""
Hugging Face Hub API ব্যবহার করে সম্পূর্ণ অটোমেটিক ফেসবুক পোস্ট স্ক্রিপ্ট।

এই ভার্সনে যা ফিক্স/যুক্ত করা হয়েছে:
- জাপানি ক্যারেক্টার বাগ ফিক্সড।
- 'provider="auto"' মোড যুক্ত করা হয়েছে (HF_PROVIDER env var দিয়ে ওভাররাইডযোগ্য),
  পুরনো huggingface_hub ভার্সনে এই প্যারামিটার না থাকলেও সেফ ফলব্যাক আছে (build_client)।
- টেক্সট ও ইমেজ — দুই ধরনের জেনারেশনেই একাধিক মডেল ফলব্যাক, যাতে একটি মডেল/প্রোভাইডার
  ডাউন থাকলেও স্ক্রিপ্ট পুরোপুরি বন্ধ না হয়ে যায়।
- রেট-লিমিট (429) ডিটেকশন করে বেশি সময় অপেক্ষা করার লজিক।
- text_to_image() থেকে PIL.Image বা raw bytes — দুই ধরনের রিটার্ন ভ্যালুই হ্যান্ডেল করা হয়।
- ইমেজ সাইজ এপিআই লেভেলে ফোর্স না করে জেনারেশনের পরে PIL দিয়ে রিসাইজ ও প্রয়োজনে
  কোয়ালিটি কমিয়ে ফেসবুকের আপলোড লিমিটের মধ্যে রাখা হয়।
- ফেসবুক পোস্টিং-এ নেটওয়ার্ক/নন-JSON রেসপন্স রিট্রাই, এবং টোকেন/পারমিশন এরর হলে
  অপ্রয়োজনীয় রিট্রাই এড়িয়ে দ্রুত ফেইল করা হয়।
- পুরো AI-জেনারেশন পাইপলাইন একটি try/except-এ মোড়ানো, যাতে cron/GitHub Actions-এ
  raw traceback না দেখিয়ে পরিষ্কার লগ ও এক্সিট কোড দেওয়া হয়।

প্রয়োজনীয় প্যাকেজ: pip install -U huggingface_hub requests Pillow
"""

import os
import random
import sys
import time
import io
import requests
from huggingface_hub import InferenceClient
from PIL import Image

FB_GRAPH_API = "https://graph.facebook.com/v21.0"

# ফেসবুকের জন্য মানানসই ল্যান্ডস্কেপ (৪:৩) টার্গেট সাইজ
TARGET_IMAGE_SIZE = (1024, 768)

# টেক্সট ও ইমেজের জন্য আলাদা আলাদা মডেল ফলব্যাক লিস্ট রাখা হলো,
# যাতে একটি মডেল/প্রোভাইডার ডাউন থাকলেও স্ক্রিপ্ট বন্ধ না হয়ে যায়।
TEXT_MODELS = [
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
]
IMAGE_MODELS = [
    "black-forest-labs/FLUX.1-schnell",
    "black-forest-labs/FLUX.1-dev",
]

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


def build_client(hf_token: str, hf_provider: str) -> InferenceClient:
    """huggingface_hub-এর পুরনো/নতুন ভার্সন উভয় ক্ষেত্রেই যাতে কাজ করে তার জন্য
    সেফ ক্লায়েন্ট ইনিশিয়ালাইজার। 'provider' প্যারামিটার পুরনো ভার্সনে না থাকতে পারে,
    তাই TypeError এলে ফলব্যাক করে সাধারণ ক্লায়েন্ট বানানো হবে।"""
    try:
        return InferenceClient(token=hf_token, provider=hf_provider, timeout=120)
    except TypeError:
        print("⚠️ এই huggingface_hub ভার্সনে 'provider'/'timeout' প্যারামিটার সাপোর্ট করছে না, ডিফল্ট ক্লায়েন্ট ব্যবহার করা হচ্ছে।")
        return InferenceClient(token=hf_token)


def _is_rate_limited(error: Exception) -> bool:
    msg = str(error)
    return "429" in msg or "rate limit" in msg.lower() or "too many requests" in msg.lower()


def get_hf_text(client: InferenceClient, instruction: str, max_tokens: int = 150) -> str:
    """Hugging Face-এর লার্জ ল্যাঙ্গুয়েজ মডেল ব্যবহার করে টেক্সট জেনারেট করার সেফ ফাংশন।
    একাধিক মডেলে ফলব্যাক করে, যাতে একটি মডেল আনঅ্যাভেইলেবল থাকলেও কাজ চলে।"""
    last_error = None
    for text_model in TEXT_MODELS:
        for attempt in range(3):
            try:
                messages = [{"role": "user", "content": instruction}]
                response = client.chat_completion(
                    model=text_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                result = response.choices[0].message.content
                if result:
                    return result.strip()
            except Exception as e:
                last_error = e
                wait = 30 if _is_rate_limited(e) else 10
                print(f"⚠️ HF টেক্সট মডেল এরর [{text_model}] (চেষ্টা {attempt + 1}): {e}")
                time.sleep(wait)
        print(f"➡️ '{text_model}' কাজ করছে না, পরের ফলব্যাক মডেলে যাওয়া হচ্ছে...")
    raise RuntimeError(f"Hugging Face টেক্সট সার্ভার থেকে রেসপন্স পাওয়া যায়নি। সর্বশেষ এরর: {last_error}")


def auto_generate_topic(client: InferenceClient) -> str:
    """Hugging Face AI ব্যবহার করে নিজে থেকে একটি নতুন এবং অনন্য টপিক তৈরি করে।"""
    print("🔍 Hugging Face AI-এর কাছ থেকে নতুন ইউনিক টপিক আইডিয়া নেওয়া হচ্ছে...")

    categories = [
        "Ancient Lost Civilization", "Mysterious Historical Event",
        "Architectural Wonder of the Past", "Mythological Kingdom",
        "Medieval Secret Castle", "Historical Underwater Ruins",
        "Futuristic Cyberpunk Cityscape", "Deep Space Exploration Wonder",
        "Surreal Steampunk Laboratory", "Nature-infused Fantasy Village",
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


def _to_pil_image(raw) -> Image.Image:
    """huggingface_hub-এর ভার্সন ভেদে text_to_image() কখনো PIL.Image, কখনো raw bytes
    রিটার্ন করতে পারে — দুটো কেসই নিরাপদে হ্যান্ডেল করা হলো।"""
    if isinstance(raw, Image.Image):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        return Image.open(io.BytesIO(raw))
    raise TypeError(f"text_to_image থেকে অপ্রত্যাশিত টাইপ পাওয়া গেছে: {type(raw)}")


def _encode_for_facebook(image: Image.Image, max_bytes: int = 4 * 1024 * 1024) -> bytes:
    """ফেসবুকের আপলোড সাইজ লিমিটের মধ্যে রাখতে প্রয়োজনে JPEG কোয়ালিটি কমিয়ে এনকোড করে।"""
    image = image.convert("RGB").resize(TARGET_IMAGE_SIZE, Image.LANCZOS)
    for quality in (90, 80, 70, 60, 50):
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality)
        data = buf.getvalue()
        if len(data) <= max_bytes:
            return data
    return data  # সর্বনিম্ন কোয়ালিটিতেও যা হয় তাই রিটার্ন করা হলো


def generate_image_hf_official(client: InferenceClient, prompt_text: str) -> bytes:
    """Hugging Face Hub লাইব্রেরি ব্যবহার করে FLUX ছবি জেনারেট করে।
    এপিআই-কে কাস্টম width/height দিয়ে ফোর্স না করে (যা কিছু প্রোভাইডারে এরর দিতে পারে),
    বরং জেনারেশনের পরে PIL দিয়ে ফেসবুক-ফ্রেন্ডলি সাইজে রিসাইজ করা হচ্ছে।"""
    last_error = None
    for image_model in IMAGE_MODELS:
        for attempt in range(3):
            try:
                print(f"🎨 Hugging Face মডেল দিয়ে ছবি জেনারেট করা হচ্ছে: {image_model} ...")
                raw_image = client.text_to_image(prompt_text, model=image_model)
                image = _to_pil_image(raw_image)
                return _encode_for_facebook(image)

            except Exception as e:
                last_error = e
                print(f"⚠️ ছবি জেনারেশন ব্যর্থ [{image_model}] (চেষ্টা {attempt + 1}): {e}")
                if "503" in str(e) or "Loading" in str(e):
                    print("⏳ মডেল লোড হতে সময় নিচ্ছে... ২০ সেকেন্ড অপেক্ষা করা হচ্ছে...")
                    time.sleep(20)
                elif _is_rate_limited(e):
                    print("⏳ রেট লিমিটে পড়েছে... ৩০ সেকেন্ড অপেক্ষা করা হচ্ছে...")
                    time.sleep(30)
                else:
                    time.sleep(10)
        print(f"➡️ '{image_model}' কাজ করছে না, পরের ফলব্যাক মডেলে যাওয়া হচ্ছে...")
    raise RuntimeError(f"Hugging Face ক্লায়েন্ট থেকে ছবি জেনারেট করা সম্ভব হয়নি। সর্বশেষ এরর: {last_error}")


def post_to_facebook(image_bytes: bytes, caption: str, token: str, page_id: str):
    """ছবি Facebook Page-এ পোস্ট করে (নিরাপদ এরর হ্যান্ডলিং ও রিট্রাই সহ)।"""
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    last_error = "অজানা ফেসবুক এরর"

    for attempt in range(3):
        try:
            files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
            data = {"message": caption, "access_token": token}
            resp = requests.post(url, data=data, files=files, timeout=90)

            try:
                result = resp.json()
            except ValueError:
                last_error = f"ফেসবুক থেকে অপ্রত্যাশিত (নন-JSON) রেসপন্স, স্ট্যাটাস কোড: {resp.status_code}"
                print(f"⚠️ {last_error} (চেষ্টা {attempt + 1})")
                time.sleep(10)
                continue

            if "id" in result:
                return True, result["id"]

            error_info = result.get("error", {})
            last_error = error_info.get("message", "অজানা ফেসবুক এরর")
            error_code = error_info.get("code")

            # টোকেন/পারমিশন সংক্রান্ত এরর হলে রিট্রাই করার মানে নেই, সাথে সাথে থামা ভালো
            if error_code in (190, 200, 10):
                return False, last_error

            print(f"⚠️ ফেসবুক পোস্ট এরর (চেষ্টা {attempt + 1}): {last_error}")
            time.sleep(10)

        except requests.exceptions.RequestException as network_error:
            last_error = f"ফেসবুক সার্ভার কানেকশন এরর: {network_error}"
            print(f"⚠️ {last_error} (চেষ্টা {attempt + 1})")
            time.sleep(10)

    return False, last_error


def main():
    style = os.environ.get("STYLE", "").strip()
    fb_token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    fb_page_id = os.environ.get("FB_PAGE_ID", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    # প্রোভাইডার অপ্রয়োজনীয় এরর এড়াতে "auto" করা হলো, চাইলে env var দিয়ে ওভাররাইড করা যাবে
    # (যেমন HF_PROVIDER=together, novita, hf-inference ইত্যাদি)
    hf_provider = os.environ.get("HF_PROVIDER", "auto").strip() or "auto"

    if not fb_token or not fb_page_id or not hf_token:
        print("❌ প্রোজেক্টের প্রয়োজনীয় টোকেনগুলো (FB বা HF) সেট করা নেই। GitHub Secrets চেক করুন।")
        sys.exit(1)

    try:
        client = build_client(hf_token, hf_provider)

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

    except Exception as pipeline_error:
        print(f"❌ AI কন্টেন্ট জেনারেশন পাইপলাইনে সমস্যা হয়েছে: {pipeline_error}")
        sys.exit(1)

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

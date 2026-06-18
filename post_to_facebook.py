"""
Auto Facebook Poster - Optimized for GitHub Actions

এই ভার্সনে যা আছে:
- 'logging' মডিউল ব্যবহার করে স্পষ্ট, টাইমস্ট্যাম্পসহ লগ (GitHub Actions লগে পড়তে সুবিধা)।
- শুরুতেই env var ভ্যালিডেশন, যাতে missing secret থাকলে দ্রুত স্পষ্ট মেসেজ দিয়ে এক্সিট হয়।
- টেক্সট ও ইমেজ — দুই ধরনের জেনারেশনেই মাল্টি-মডেল ফলব্যাক + প্রতি মডেলে একাধিক রিট্রাই।
- রেট-লিমিট (429) ডিটেকশন করে বেশি সময় অপেক্ষা করার লজিক।
- 'provider' প্যারামিটার পুরনো huggingface_hub ভার্সনে না থাকলেও সেফ ফলব্যাক (build_client)।
- ক্যাপশন জেনারেশন ব্যর্থ হলেও ডিফল্ট বাংলা ক্যাপশন দিয়ে পোস্ট চালিয়ে যাওয়া হয়, পুরো রান আটকায় না।
- text_to_image() থেকে PIL.Image বা raw bytes — দুই ধরনের রিটার্নই হ্যান্ডেল করা।
- ইমেজ রিসাইজ ও প্রয়োজনে কোয়ালিটি কমিয়ে ফেসবুকের আপলোড সাইজ লিমিটের মধ্যে রাখা।
- ফেসবুক পোস্টিং-এ নেটওয়ার্ক/নন-JSON রেসপন্স রিট্রাই, টোকেন/পারমিশন এরর হলে দ্রুত ফেইল করা।
- টপিক ক্যাটাগরি ও অ্যাঙ্গেল-হিন্ট লিস্ট রাখা হয়েছে, যাতে পোস্টগুলো সময়ের সাথে রিপিটেটিভ না হয়।

প্রয়োজনীয় প্যাকেজ: pip install -U huggingface_hub requests Pillow
"""

import os
import random
import sys
import time
import io
import logging
import requests
from huggingface_hub import InferenceClient
from PIL import Image

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FB_GRAPH_API = "https://graph.facebook.com/v21.0"
TARGET_IMAGE_SIZE = (1024, 768)

TEXT_MODELS = ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.1-8B-Instruct"]
IMAGE_MODELS = ["black-forest-labs/FLUX.1-schnell", "black-forest-labs/FLUX.1-dev"]

TOPIC_CATEGORIES = [
    "Ancient Lost Civilization", "Mysterious Historical Event",
    "Architectural Wonder of the Past", "Mythological Kingdom",
    "Medieval Secret Castle", "Historical Underwater Ruins",
    "Futuristic Cyberpunk Cityscape", "Deep Space Exploration Wonder",
    "Surreal Steampunk Laboratory", "Nature-infused Fantasy Village",
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

DEFAULT_CAPTION = "ইতিহাস আর কল্পনার পাতা থেকে এক রহস্যময় ঝলক... 📜🎨\n\n#AIArt #DigitalArt"


def build_client(hf_token: str, hf_provider: str) -> InferenceClient:
    """পুরনো huggingface_hub ভার্সনে 'provider'/'timeout' প্যারামিটার না থাকলে সেফ ফলব্যাক।"""
    try:
        return InferenceClient(token=hf_token, provider=hf_provider, timeout=180)
    except TypeError:
        logger.warning("এই huggingface_hub ভার্সনে provider/timeout সাপোর্ট নেই, ডিফল্ট ক্লায়েন্ট ব্যবহার করা হচ্ছে।")
        return InferenceClient(token=hf_token)


def _is_rate_limited(error: Exception) -> bool:
    msg = str(error).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg


def get_hf_text(client: InferenceClient, instruction: str, max_tokens: int = 200) -> str:
    """মাল্টি-মডেল + প্রতি মডেলে একাধিক রিট্রাই সহ টেক্সট জেনারেশন।"""
    last_error = None
    for model in TEXT_MODELS:
        for attempt in range(3):
            try:
                response = client.chat_completion(
                    model=model,
                    messages=[{"role": "user", "content": instruction}],
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                result = response.choices[0].message.content
                if result:
                    return result.strip()
            except Exception as e:
                last_error = e
                wait = 30 if _is_rate_limited(e) else 8
                logger.warning(f"টেক্সট মডেল {model} ব্যর্থ (চেষ্টা {attempt + 1}/3): {e}")
                time.sleep(wait)
        logger.info(f"'{model}' কাজ করছে না, পরের ফলব্যাক মডেলে যাওয়া হচ্ছে...")
    raise RuntimeError(f"টেক্সট জেনারেশন পুরোপুরি ব্যর্থ। সর্বশেষ এরর: {last_error}")


def auto_generate_topic(client: InferenceClient) -> str:
    chosen_cat = random.choice(TOPIC_CATEGORIES)
    instruction = (
        f"Give me exactly one interesting, specific, and unique image idea/topic about a '{chosen_cat}'. "
        "It should be suitable for creating a stunning visual. Output ONLY the topic name in one short "
        "sentence, no quotes, no intro, no explanation."
    )
    topic = get_hf_text(client, instruction, max_tokens=50)
    return topic or "Mysterious Ancient Civilization"


def generate_prompt(client: InferenceClient, topic: str, style: str) -> str:
    hint = random.choice(ANGLE_HINTS)
    instruction = (
        "You generate image-generation prompts. Output exactly ONE creative, highly specific, detailed "
        f'English image-generation prompt related to the topic "{topic}", {hint}. Output ONLY the prompt '
        "text itself, nothing else, no quotes, no numbering."
    )
    prompt = get_hf_text(client, instruction, max_tokens=150)
    if not prompt:
        raise RuntimeError("AI prompt তৈরি করতে ব্যর্থ হয়েছে")
    return f"{prompt}, {style}" if style else prompt


def generate_caption(client: InferenceClient, prompt_text: str) -> str:
    """ব্যর্থ হলেও ডিফল্ট বাংলা ক্যাপশন রিটার্ন করে, যাতে পুরো পাইপলাইন না থেমে যায়।"""
    instruction = (
        "Write exactly one short, catchy Facebook caption in Bengali (with 1-2 relevant emojis like "
        f'📜, 🏛️, 🎨, 🌌) for an AI-generated image described as: "{prompt_text}". Also include 3-4 '
        "relevant English hashtags at the very end (e.g., #AIArt #MidjourneyStyle). Output only the "
        "caption text and hashtags, nothing else. Do not use sparkle symbols like ✨."
    )
    try:
        caption = get_hf_text(client, instruction, max_tokens=150)
        caption = caption.replace("✨", "📜").replace("❇️", "🏛️").strip('"').strip("'")
        return caption or DEFAULT_CAPTION
    except Exception as e:
        logger.warning(f"ক্যাপশন জেনারেশন ব্যর্থ, ডিফল্ট ক্যাপশন ব্যবহার করা হচ্ছে: {e}")
        return DEFAULT_CAPTION


def _to_pil_image(raw) -> Image.Image:
    if isinstance(raw, Image.Image):
        return raw
    if isinstance(raw, (bytes, bytearray)):
        return Image.open(io.BytesIO(raw))
    raise TypeError(f"text_to_image থেকে অপ্রত্যাশিত টাইপ পাওয়া গেছে: {type(raw)}")


def _encode_for_facebook(image: Image.Image, max_bytes: int = 4 * 1024 * 1024) -> bytes:
    """ফেসবুকের আপলোড সাইজ লিমিটের মধ্যে রাখতে প্রয়োজনে JPEG কোয়ালিটি কমিয়ে এনকোড করে।"""
    image = image.convert("RGB").resize(TARGET_IMAGE_SIZE, Image.LANCZOS)
    for quality in (85, 75, 65, 55):
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality)
        data = buf.getvalue()
        if len(data) <= max_bytes:
            return data
    return data


def generate_image_hf(client: InferenceClient, prompt: str) -> bytes:
    """মাল্টি-মডেল + প্রতি মডেলে একাধিক রিট্রাই সহ ইমেজ জেনারেশন।"""
    last_error = None
    for model in IMAGE_MODELS:
        for attempt in range(3):
            try:
                logger.info(f"ইমেজ জেনারেট হচ্ছে: {model} (চেষ্টা {attempt + 1}/3)")
                raw = client.text_to_image(prompt, model=model)
                img = _to_pil_image(raw)
                return _encode_for_facebook(img)
            except Exception as e:
                last_error = e
                logger.warning(f"ইমেজ মডেল {model} ব্যর্থ: {e}")
                if "503" in str(e) or "Loading" in str(e):
                    logger.info("মডেল লোড হতে সময় নিচ্ছে... ২০ সেকেন্ড অপেক্ষা করা হচ্ছে...")
                    time.sleep(20)
                elif _is_rate_limited(e):
                    logger.info("রেট লিমিটে পড়েছে... ৩০ সেকেন্ড অপেক্ষা করা হচ্ছে...")
                    time.sleep(30)
                else:
                    time.sleep(10)
        logger.info(f"'{model}' কাজ করছে না, পরের ফলব্যাক মডেলে যাওয়া হচ্ছে...")
    raise RuntimeError(f"ছবি জেনারেশন ব্যর্থ। সর্বশেষ এরর: {last_error}")


def post_to_facebook(image_bytes: bytes, caption: str, token: str, page_id: str) -> bool:
    """রিট্রাই ও নিরাপদ JSON পার্সিং সহ ফেসবুক পোস্টিং। সফল হলে True, ব্যর্থ হলে False রিটার্ন করে।"""
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
                last_error = f"নন-JSON রেসপন্স, স্ট্যাটাস কোড: {resp.status_code}"
                logger.warning(f"{last_error} (চেষ্টা {attempt + 1}/3)")
                time.sleep(10)
                continue

            if "id" in result:
                logger.info(f"পোস্ট সফল! Post ID: {result['id']}")
                return True

            error_info = result.get("error", {})
            last_error = error_info.get("message", "অজানা ফেসবুক এরর")
            error_code = error_info.get("code")

            # টোকেন/পারমিশন সংক্রান্ত এরর হলে রিট্রাই না করে সাথে সাথে থামা ভালো
            if error_code in (190, 200, 10):
                logger.error(f"ফেসবুক টোকেন/পারমিশন এরর: {last_error}")
                return False

            logger.warning(f"ফেসবুক পোস্ট এরর (চেষ্টা {attempt + 1}/3): {last_error}")
            time.sleep(10)

        except requests.exceptions.RequestException as network_error:
            last_error = f"নেটওয়ার্ক কানেকশন এরর: {network_error}"
            logger.warning(f"{last_error} (চেষ্টা {attempt + 1}/3)")
            time.sleep(10)

    logger.error(f"ফেসবুক পোস্ট ব্যর্থ: {last_error}")
    return False


def main():
    logger.info("পাইপলাইন শুরু হচ্ছে...")

    style = os.environ.get("STYLE", "").strip()
    fb_token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    fb_page_id = os.environ.get("FB_PAGE_ID", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    hf_provider = os.environ.get("HF_PROVIDER", "auto").strip() or "auto"

    if not fb_token or not fb_page_id or not hf_token:
        logger.error("প্রয়োজনীয় টোকেন (FB_PAGE_TOKEN / FB_PAGE_ID / HF_TOKEN) সেট করা নেই। GitHub Secrets চেক করুন।")
        sys.exit(1)

    try:
        client = build_client(hf_token, hf_provider)

        topic = auto_generate_topic(client)
        logger.info(f"AI জেনারেটেড টপিক: {topic}")

        prompt = generate_prompt(client, topic, style)
        logger.info(f"প্রম্পট রেডি: {prompt}")

        caption = generate_caption(client, prompt)
        logger.info(f"ক্যাপশন রেডি:\n{caption}")

        img_bytes = generate_image_hf(client, prompt)
        logger.info(f"ছবি সফলভাবে জেনারেট হয়েছে ({len(img_bytes)} bytes)")

    except Exception as pipeline_error:
        logger.error(f"AI কন্টেন্ট জেনারেশন পাইপলাইনে সমস্যা হয়েছে: {pipeline_error}")
        sys.exit(1)

    success = post_to_facebook(img_bytes, caption, fb_token, fb_page_id)
    if not success:
        sys.exit(1)

    logger.info("কাজ শেষ!")


if __name__ == "__main__":
    main()

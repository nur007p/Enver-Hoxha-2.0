"""
Auto Facebook Poster - Optimized for GitHub Actions
FileName: post_to_facebook.py
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

# লগার সেটআপ
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

DEFAULT_CAPTION = "ইতিহাস আর কল্পনার পাতা থেকে এক রহস্যময় ঝলক... 📜🎨\n\n#History #Mystery #Fantasy"

def build_client(hf_token: str, hf_provider: str) -> InferenceClient:
    try:
        return InferenceClient(token=hf_token, provider=hf_provider, timeout=180)
    except TypeError:
        return InferenceClient(token=hf_token)

def _is_rate_limited(error: Exception) -> bool:
    msg = str(error).lower()
    return "429" in msg or "rate limit" in msg or "too many requests" in msg

def get_hf_text(client: InferenceClient, instruction: str, max_tokens: int = 200) -> str:
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
    raise RuntimeError(f"টেক্সট জেনারেশন পুরোপুরি ব্যর্থ। সর্বশেষ এরর: {last_error}")

def auto_generate_topic(client: InferenceClient) -> str:
    chosen_cat = random.choice(TOPIC_CATEGORIES)
    instruction = (
        f"Give me exactly one interesting, specific, and unique image idea/topic about a '{chosen_cat}'. "
        "It should be suitable for creating a stunning visual. Output ONLY the topic name, no quotes."
    )
    return get_hf_text(client, instruction, max_tokens=50)

def generate_prompt(client: InferenceClient, topic: str, style: str) -> str:
    hint = random.choice(ANGLE_HINTS)
    instruction = (
        "You generate image-generation prompts. Output exactly ONE creative, highly specific, detailed "
        f'English image-generation prompt related to the topic "{topic}", {hint}. Output ONLY the prompt.'
    )
    prompt = get_hf_text(client, instruction, max_tokens=150)
    return f"{prompt}, {style}" if style else prompt

def generate_caption(client: InferenceClient, prompt_text: str) -> str:
    instruction = (
        "Write exactly one short, catchy Facebook caption in Bengali (with 1-2 relevant emojis like "
        f'📜, 🏛️, 🎨, 🌌) for an image described as: "{prompt_text}". Also include 3-4 '
        "relevant English hashtags related to the subject ONLY (e.g., #History #Mystery #Fantasy). "
        "Strictly Do not use #AIArt, #ArtificialIntelligence, or any tags related to AI. "
        "Output only the caption text and hashtags, nothing else."
    )
    try:
        caption = get_hf_text(client, instruction, max_tokens=150)
        return caption.strip('"').strip("'")
    except Exception as e:
        logger.warning(f"ক্যাপশন জেনারেশন ব্যর্থ, ডিফল্ট ক্যাপশন ব্যবহার হচ্ছে: {e}")
        return DEFAULT_CAPTION

def _to_pil_image(raw) -> Image.Image:
    if isinstance(raw, Image.Image): return raw
    if isinstance(raw, (bytes, bytearray)): return Image.open(io.BytesIO(raw))
    raise TypeError("Unexpected type from text_to_image")

def _encode_for_facebook(image: Image.Image, max_bytes: int = 4 * 1024 * 1024) -> bytes:
    image = image.convert("RGB").resize(TARGET_IMAGE_SIZE, Image.LANCZOS)
    for quality in (85, 75, 65, 55):
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=quality)
        data = buf.getvalue()
        if len(data) <= max_bytes: return data
    return data

def generate_image_hf(client: InferenceClient, prompt: str) -> bytes:
    for model in IMAGE_MODELS:
        try:
            logger.info(f"ইমেজ জেনারেট হচ্ছে: {model}")
            raw = client.text_to_image(prompt, model=model)
            return _encode_for_facebook(_to_pil_image(raw))
        except Exception as e:
            logger.warning(f"ইমেজ মডেল {model} ব্যর্থ: {e}")
            time.sleep(10)
    raise RuntimeError("ছবি জেনারেশন ব্যর্থ।")

def post_to_facebook(image_bytes: bytes, caption: str, token: str, page_id: str) -> bool:
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    for attempt in range(3):
        try:
            resp = requests.post(url, data={"message": caption, "access_token": token}, 
                                 files={"source": ("image.jpg", image_bytes, "image/jpeg")}, timeout=90)
            result = resp.json()
            if "id" in result: return True
            logger.warning(f"ফেসবুক পোস্ট এরর: {result.get('error')}")
        except Exception as e:
            logger.warning(f"ফেসবুক পোস্ট ব্যর্থ (চেষ্টা {attempt+1}/3): {e}")
        time.sleep(10)
    return False

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    fb_page_id = os.environ.get("FB_PAGE_ID", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    
    if not all([fb_token, fb_page_id, hf_token]):
        logger.error("প্রয়োজনীয় সিক্রেট সেট করা নেই!")
        sys.exit(1)

    client = build_client(hf_token, os.environ.get("HF_PROVIDER", "auto"))
    topic = auto_generate_topic(client)
    prompt = generate_prompt(client, topic, os.environ.get("STYLE", ""))
    caption = generate_caption(client, prompt)
    img_bytes = generate_image_hf(client, prompt)
    
    if post_to_facebook(img_bytes, caption, fb_token, fb_page_id):
        logger.info("কাজ শেষ!")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()

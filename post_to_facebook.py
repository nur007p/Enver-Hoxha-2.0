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

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FB_GRAPH_API = "https://graph.facebook.com/v21.0"
TARGET_IMAGE_SIZE = (1024, 768)

TEXT_MODELS = ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.1-8B-Instruct"]
IMAGE_MODELS = ["black-forest-labs/FLUX.1-schnell", "black-forest-labs/FLUX.1-dev"]

# ভিউ বাড়ানোর জন্য ২০টি ক্যাটাগরি
TOPIC_CATEGORIES = [
    "Ancient Lost Civilization", "Mysterious Historical Event",
    "Architectural Wonder of the Past", "Mythological Kingdom",
    "Medieval Secret Castle", "Historical Underwater Ruins",
    "Futuristic Cyberpunk Cityscape", "Deep Space Exploration Wonder",
    "Surreal Steampunk Laboratory", "Nature-infused Fantasy Village",
    "Unsolved Historical Mystery", "Traditional Bengali Village Life",
    "Ancient Scientific Innovation", "Nature's Hidden Paradise",
    "Majestic Wildlife in Wild Habitat", "Floating Islands in the Sky",
    "Forgotten Treasure in a Jungle", "Bioluminescent Enchanted Forest",
    "Intergalactic Trading Space Station", "Zen Temple on a Misty Mountain"
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
                if _is_rate_limited(e):
                    break
                wait = 8 * (attempt + 1)
                time.sleep(wait)
    raise RuntimeError(f"টেক্সট জেনারেশন ব্যর্থ। সর্বশেষ এরর: {last_error}")

def auto_generate_topic(client: InferenceClient) -> str:
    chosen_cat = random.choice(TOPIC_CATEGORIES)
    instruction = (
        f"Give me exactly one interesting, specific, and unique image idea/topic about a '{chosen_cat}'. "
        "Output ONLY the topic name, no quotes."
    )
    return get_hf_text(client, instruction, max_tokens=50)

def generate_prompt(client: InferenceClient, topic: str, style: str) -> str:
    hint = random.choice(ANGLE_HINTS)
    instruction = (
        "Generate a detailed, creative image prompt related to "
        f'"{topic}", {hint}. Output ONLY the prompt text.'
    )
    prompt = get_hf_text(client, instruction, max_tokens=150)
    return f"{prompt}, {style}" if style else prompt

def generate_caption(client: InferenceClient, prompt_text: str) -> str:
    instruction = (
        "Write a short, catchy Facebook caption in Bengali (with 1-2 relevant emojis like 📜, 🏛️, 🎨) "
        f'for an image described as: "{prompt_text}". Also include 3-4 relevant English hashtags '
        "related to the subject. Do not use AI-related hashtags. Output ONLY the caption and tags."
    )
    try:
        caption = get_hf_text(client, instruction, max_tokens=150)
        return caption.strip('"').strip("'")
    except:
        return DEFAULT_CAPTION

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
            raw = client.text_to_image(prompt, model=model)
            img = raw if isinstance(raw, Image.Image) else Image.open(io.BytesIO(raw))
            return _encode_for_facebook(img)
        except Exception:
            time.sleep(10)
    raise RuntimeError("ছবি জেনারেশন ব্যর্থ।")

def post_to_facebook(image_bytes: bytes, caption: str, token: str, page_id: str) -> bool:
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    try:
        resp = requests.post(url, data={"message": caption, "access_token": token}, 
                             files={"source": ("image.jpg", image_bytes, "image/jpeg")}, timeout=90)
        return "id" in resp.json()
    except:
        return False

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN", "").strip()
    fb_page_id = os.environ.get("FB_PAGE_ID", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    
    if not all([fb_token, fb_page_id, hf_token]):
        sys.exit(1)

    client = build_client(hf_token, os.environ.get("HF_PROVIDER", "auto"))
    topic = auto_generate_topic(client)
    prompt = generate_prompt(client, topic, os.environ.get("STYLE", ""))
    caption = generate_caption(client, prompt)
    img_bytes = generate_image_hf(client, prompt)
    
    if not post_to_facebook(img_bytes, caption, fb_token, fb_page_id):
        sys.exit(1)

if __name__ == "__main__":
    main()

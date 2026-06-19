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

TEXT_MODELS = ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.1-70B-Instruct"]
IMAGE_MODELS = ["black-forest-labs/FLUX.1-schnell", "black-forest-labs/FLUX.1-dev"]

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
    "from an unusual or creative camera angle", "with dramatic, moody lighting",
    "in a candid, everyday moment", "with a unique and vivid color palette",
    "with an interesting, well-balanced composition", "showing fine detail and texture up close",
    "during golden hour with warm light", "with a cinematic, atmospheric mood",
    "from a wide establishing shot perspective", "with a minimalist, clean aesthetic",
]

DEFAULT_CAPTION = "ইতিহাস আর কল্পনার পাতা থেকে এক রহস্যময় ঝলক... 📜🎨\n\n#History #Mystery #Fantasy"

def build_client(hf_token: str, hf_provider: str) -> InferenceClient:
    try:
        return InferenceClient(token=hf_token, provider=hf_provider, timeout=180)
    except Exception:
        return InferenceClient(token=hf_token)

def get_hf_text(client: InferenceClient, instruction: str, max_tokens: int = 400) -> str:
    for model in TEXT_MODELS:
        try:
            response = client.chat_completion(
                model=model,
                messages=[{"role": "user", "content": instruction}],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            continue
    return DEFAULT_CAPTION

def auto_generate_topic(client: InferenceClient) -> str:
    chosen_cat = random.choice(TOPIC_CATEGORIES)
    instruction = f"Give me exactly one unique image topic related to '{chosen_cat}'. Output ONLY the topic name."
    return get_hf_text(client, instruction, max_tokens=30)

def generate_prompt(client: InferenceClient, topic: str, style: str) -> str:
    hint = random.choice(ANGLE_HINTS)
    instruction = f"Generate a detailed, creative image generation prompt for: '{topic}', {hint}. Output ONLY the prompt."
    return get_hf_text(client, instruction, max_tokens=150)

def generate_caption(client: InferenceClient, prompt_text: str) -> str:
    # প্রম্পটটিকে ইনপুট হিসেবে দিয়ে ক্যাপশন জেনারেট করা হচ্ছে যাতে সামঞ্জস্য থাকে
    instruction = (
        f"Based on this image description: '{prompt_text}', write a catchy, storytelling-style "
        "Facebook caption in Bengali. Start with a mysterious hook or question. "
        "Include 2-3 relevant emojis. End with 3 trending hashtags. "
        "Output ONLY the caption text."
    )
    return get_hf_text(client, instruction, max_tokens=350)

def generate_image_hf(client: InferenceClient, prompt: str) -> bytes:
    for model in IMAGE_MODELS:
        try:
            raw = client.text_to_image(prompt, model=model)
            img = raw if isinstance(raw, Image.Image) else Image.open(io.BytesIO(raw))
            # Image encoding
            buf = io.BytesIO()
            img.convert("RGB").resize(TARGET_IMAGE_SIZE, Image.LANCZOS).save(buf, format="JPEG", quality=85)
            return buf.getvalue()
        except Exception:
            continue
    raise RuntimeError("ছবি তৈরি করা সম্ভব হয়নি।")

def post_to_facebook(image_bytes, caption, token, page_id):
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    data = {"message": caption, "access_token": token}
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    resp = requests.post(url, data=data, files=files, timeout=90)
    return "id" in resp.json()

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    fb_page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")
    
    if not all([fb_token, fb_page_id, hf_token]):
        sys.exit(1)

    client = build_client(hf_token, os.environ.get("HF_PROVIDER", "auto"))
    
    topic = auto_generate_topic(client)
    prompt = generate_prompt(client, topic, os.environ.get("STYLE", ""))
    caption = generate_caption(client, prompt) # প্রম্পট থেকে ক্যাপশন তৈরি
    img_bytes = generate_image_hf(client, prompt)
    
    if not post_to_facebook(img_bytes, caption, fb_token, fb_page_id):
        sys.exit(1)

if __name__ == "__main__":
    main()

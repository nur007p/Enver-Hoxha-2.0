import os
import random
import sys
import io
import logging
import requests
from huggingface_hub import InferenceClient
from PIL import Image

# লগের ফরম্যাট সেটআপ
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
    "Forgotten Treasure in a Jungle", "Bioluminescent Enchanted Forest"
]

def build_client(hf_token: str) -> InferenceClient:
    return InferenceClient(token=hf_token)

def get_hf_text(client: InferenceClient, instruction: str, max_tokens: int = 800) -> str:
    for model in TEXT_MODELS:
        try:
            response = client.chat_completion(
                model=model,
                messages=[{"role": "user", "content": instruction}],
                max_tokens=max_tokens,
                temperature=0.6,
            )
            content = response.choices[0].message.content.strip()
            # যদি ক্যাপশন অসম্পূর্ণ মনে হয়, তবে একটি ডট যোগ করে পূর্ণতা দেওয়া
            if len(content) > 100 and not content.endswith(('.', '!', '?', '#')):
                content += "..."
            return content
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
    return "রহস্যময় এই দৃশ্যটি আপনার কল্পনাকে রাঙিয়ে তুলুক। 📜🎨"

def generate_image_and_data(client: InferenceClient):
    # ১. বিষয় নির্বাচন
    topic = random.choice(TOPIC_CATEGORIES)
    
    # ২. প্রম্পট তৈরি
    prompt_instr = f"Create a high-quality, detailed AI image prompt for: '{topic}'. Output ONLY the prompt."
    prompt = get_hf_text(client, prompt_instr, max_tokens=150)
    logger.info(f"Generated Prompt: {prompt}")

    # ৩. ক্যাপশন তৈরি (স্ট্রং ইনস্ট্রাকশন)
    caption_instr = (
        f"Context: '{prompt}'. "
        "Write a storytelling-style Facebook caption in Bengali. "
        "Rules: 1. Start with an intriguing hook. 2. Describe the scene vividly and poetically. "
        "3. Keep it within 3 short paragraphs. "
        "4. End with 4-5 relevant hashtags. "
        "5. IMPORTANT: Your response must be complete, do not leave sentences hanging."
    )
    caption = get_hf_text(client, caption_instr, max_tokens=600)
    
    # ৪. ছবি তৈরি
    for model in IMAGE_MODELS:
        try:
            raw = client.text_to_image(prompt, model=model)
            img = raw if isinstance(raw, Image.Image) else Image.open(io.BytesIO(raw))
            buf = io.BytesIO()
            img.convert("RGB").resize(TARGET_IMAGE_SIZE, Image.LANCZOS).save(buf, format="JPEG", quality=85)
            return buf.getvalue(), caption
        except Exception as e:
            logger.warning(f"Image generation failed with {model}: {e}")
            continue
    raise RuntimeError("Image generation failed.")

def post_to_facebook(image_bytes, caption, token, page_id):
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    data = {"message": caption, "access_token": token}
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    
    try:
        resp = requests.post(url, data=data, files=files, timeout=90)
        result = resp.json()
        if "id" in result:
            logger.info(f"Successfully posted! Post ID: {result['id']}")
            return True
        else:
            logger.error(f"Facebook API Error: {result}")
            return False
    except Exception as e:
        logger.error(f"Request failed: {e}")
        return False

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    fb_page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")
    
    if not all([fb_token, fb_page_id, hf_token]):
        logger.error("Missing environment variables.")
        sys.exit(1)

    client = build_client(hf_token)
    img_bytes, caption = generate_image_and_data(client)
    
    if not post_to_facebook(img_bytes, caption, fb_token, fb_page_id):
        sys.exit(1)

if __name__ == "__main__":
    main()

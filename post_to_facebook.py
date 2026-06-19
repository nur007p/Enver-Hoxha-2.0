import os
import random
import sys
import io
import logging
import requests
from huggingface_hub import InferenceClient

# লগের ফরম্যাট সেটআপ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FB_GRAPH_API = "https://graph.facebook.com/v21.0"

# টেক্সট জেনারেশনের জন্য মডেল
TEXT_MODELS = ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.1-70B-Instruct"]

TOPIC_CATEGORIES = [
    "Ancient Lost Civilization in the Amazon", "Mysterious Historical Event from 19th Century",
    "Futuristic Cyberpunk Cityscape at Night", "Deep Space Exploration Wonder",
    "Traditional Bengali Village Life during Harvest", "Ethereal Spirit of the Sundarbans Mangrove"
    # বাকি বিষয়গুলো এখানে থাকবে
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
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Text model {model} failed: {e}")
    return "রহস্যময় এই দৃশ্যটি আপনার কল্পনাকে রাঙিয়ে তুলুক।"

def generate_image_and_data(client: InferenceClient):
    topic = random.choice(TOPIC_CATEGORIES)

    # প্রম্পট জেনারেশন
    prompt_instr = f"Create a descriptive, high-quality AI image prompt for: '{topic}'. Output ONLY the prompt."
    prompt = get_hf_text(client, prompt_instr, max_tokens=150)

    # ক্যাপশন জেনারেশন
    caption_instr = (
        f"Image Subject: '{prompt}'. "
        "Write a natural, storytelling-style Facebook caption in Bengali. "
        "Rules: 1. Start with a hook. 2. Keep it within 3-4 short, flowing sentences. "
        "3. End with 4-5 relevant hashtags."
    )
    caption = get_hf_text(client, caption_instr, max_tokens=400)

    # Pollinations.ai দিয়ে ইমেজ জেনারেশন
    logger.info(f"Generating image with prompt: {prompt}")
    safe_prompt = requests.utils.quote(prompt)
    image_url = f"https://pollinations.ai/p/{safe_prompt}?width=1024&height=768&nologo=true&seed={random.randint(1, 10000)}"
    
    try:
        response = requests.get(image_url, timeout=60)
        if response.status_code == 200:
            logger.info("Image generated successfully with Pollinations.ai")
            return response.content, caption
        else:
            raise RuntimeError(f"Pollinations API failed with status: {response.status_code}")
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise

def post_to_facebook(image_bytes, caption, token, page_id):
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    data = {"message": caption, "access_token": token}
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}

    try:
        resp = requests.post(url, data=data, files=files, timeout=90)
        result = resp.json()
        if "id" in result:
            logger.info(f"Successfully posted! ID: {result['id']}")
            return True
        else:
            logger.error(f"Facebook API Error: {result}")
            return False
    except Exception as e:
        logger.error(f"Posting failed: {e}")
        return False

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    fb_page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")

    if not all([fb_token, fb_page_id, hf_token]):
        logger.error("Environment variables missing.")
        sys.exit(1)

    client = build_client(hf_token)
    img_bytes, caption = generate_image_and_data(client)

    if not post_to_facebook(img_bytes, caption, fb_token, fb_page_id):
        sys.exit(1)

if __name__ == "__main__":
    main()

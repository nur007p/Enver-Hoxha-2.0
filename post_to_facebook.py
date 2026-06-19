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
TARGET_IMAGE_SIZE = (1080, 1920) 

# টেক্সট জেনারেশনের জন্য মডেল
TEXT_MODEL = "meta-llama/Llama-3.1-70B-Instruct"
# ফ্রি ইমেজ জেনারেশন মডেল (এটি সাধারণত ক্রেডিটের ঝামেলা ছাড়াই কাজ করে)
IMAGE_MODEL_ID = "runwayml/stable-diffusion-v1-5"

TOPIC_CATEGORIES = [
    "Ancient Lost Civilization in the Amazon", "Mysterious Historical Event from 19th Century",
    "Architectural Wonder of a Lost Empire", "Medieval Secret Castle in the Alps",
    "Forgotten Treasure in a dense Jungle", "Secret Passage in an Egyptian Pyramid",
    "Futuristic Cyberpunk Cityscape at Night", "Floating Islands in the Sky",
    "Bioluminescent Enchanted Forest", "Ethereal Spirit of the Sundarbans Mangrove",
    "Haunted Lighthouse on a Rocky Cliff", "A Waterfall Flowing into the Void"
]

def generate_image_and_data(hf_token: str):
    client = InferenceClient(token=hf_token)
    topic = random.choice(TOPIC_CATEGORIES)
    
    prompt = f"Cinematic photorealistic shot of {topic}, mysterious atmosphere, 8k resolution."
    
    try:
        # টেক্সট জেনারেশন
        chat_resp = client.chat_completion(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": f"Write a short, engaging Bengali storytelling caption about '{topic}'. Add 4-5 hashtags."}]
        )
        caption = chat_resp.choices[0].message.content.strip()

        # ইমেজ জেনারেশন
        image = client.text_to_image(prompt, model=IMAGE_MODEL_ID)
        
        buf = io.BytesIO()
        image.convert("RGB").resize(TARGET_IMAGE_SIZE).save(buf, format="JPEG", quality=90)
        return buf.getvalue(), caption
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise RuntimeError("Image generation failed.")

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
            logger.error(f"Facebook error: {result}")
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

    img_bytes, caption = generate_image_and_data(hf_token)
    if not post_to_facebook(img_bytes, caption, fb_token, fb_page_id):
        sys.exit(1)

if __name__ == "__main__":
    main()

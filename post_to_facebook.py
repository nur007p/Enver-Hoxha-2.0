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
TARGET_IMAGE_SIZE = (1080, 1080) # পোস্টের জন্য আদর্শ সাইজ

# ফ্রি মডেলসমূহ
TEXT_MODEL = "mistralai/Mistral-7B-Instruct-v0.3"
IMAGE_MODEL_ID = "stabilityai/stable-diffusion-2-1" 

TOPIC_CATEGORIES = [
    "Ancient mystery, cinematic style", "Forgotten forest, ethereal photography",
    "Futuristic city at night, neon lights", "Mythical underwater kingdom, 8k"
]

def generate_image_and_data(hf_token: str):
    # InferenceClient কে সরাসরি টোকেন দিয়ে তৈরি করুন
    client = InferenceClient(api_key=hf_token)
    topic = random.choice(TOPIC_CATEGORIES)
    
    try:
        # টেক্সট জেনারেশন
        chat_resp = client.chat_completion(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": f"Write a short Bengali caption about {topic}. Add hashtags."}]
        )
        caption = chat_resp.choices[0].message.content.strip()

        # ইমেজ জেনারেশন - সরাসরি ক্লায়েন্ট ব্যবহার করে
        image = client.text_to_image(prompt=topic, model=IMAGE_MODEL_ID)
        
        buf = io.BytesIO()
        image.convert("RGB").resize(TARGET_IMAGE_SIZE).save(buf, format="JPEG", quality=85)
        return buf.getvalue(), caption
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise RuntimeError("Image generation failed.")

def post_to_facebook(image_bytes, caption, token, page_id):
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    data = {"message": caption, "access_token": token}
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    
    resp = requests.post(url, data=data, files=files)
    if resp.status_code == 200:
        logger.info("Posted successfully!")
        return True
    else:
        logger.error(f"FB Error: {resp.text}")
        return False

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    fb_page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")
    
    if not all([fb_token, fb_page_id, hf_token]):
        logger.error("Missing credentials.")
        sys.exit(1)

    img_bytes, caption = generate_image_and_data(hf_token)
    post_to_facebook(img_bytes, caption, fb_token, fb_page_id)

if __name__ == "__main__":
    main()

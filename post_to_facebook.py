import os
import random
import io
import logging
import requests
from huggingface_hub import InferenceClient

# লগের ফরম্যাট সেটআপ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ফ্রি এবং স্ট্যাবল মডেল
TEXT_MODEL = "Qwen/Qwen2.5-72B-Instruct"
IMAGE_MODEL = "runwayml/stable-diffusion-v1-5"

def generate_content(hf_token):
    client = InferenceClient(api_key=hf_token)
    topic = random.choice(["Ancient ruins", "Mysterious forest", "Futuristic city"])
    
    # টেক্সট জেনারেশন
    chat_resp = client.chat_completion(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": f"Write a short Bengali caption about {topic}. Add hashtags."}]
    )
    caption = chat_resp.choices[0].message.content.strip()

    # ইমেজ জেনারেশন
    image = client.text_to_image(prompt=topic, model=IMAGE_MODEL)
    buf = io.BytesIO()
    image.convert("RGB").resize((1080, 1080)).save(buf, format="JPEG", quality=90)
    
    return buf.getvalue(), caption

def post_to_facebook(image_bytes, caption, fb_token, page_id):
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    data = {
        "message": caption, 
        "access_token": fb_token,
        "published": "true"
    }
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    
    # ফেসবুকের রিপ্লাই ক্যাপচার করা
    resp = requests.post(url, data=data, files=files)
    result = resp.json()
    
    # এটি লগে দেখাবে ফেসবুক কেন পোস্ট নিচ্ছে না (বা আইডি দিচ্ছে)
    logger.info(f"Facebook API Response: {result}")
    
    return "id" in result

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")

    if not all([fb_token, page_id, hf_token]):
        logger.error("Environment variables missing!")
        return

    try:
        img_data, caption = generate_content(hf_token)
        if post_to_facebook(img_data, caption, fb_token, page_id):
            logger.info("Successfully posted!")
        else:
            logger.error("Facebook post failed.")
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()

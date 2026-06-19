import os
import random
import io
import logging
import requests
from huggingface_hub import InferenceClient

# লগের ফরম্যাট সেটআপ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# সঠিক ফ্রি মডেলসমূহ
TEXT_MODEL = "Qwen/Qwen2.5-72B-Instruct"
IMAGE_MODEL = "runwayml/stable-diffusion-v1-5"

def generate_content(hf_token):
    client = InferenceClient(api_key=hf_token)
    topic = random.choice(["Ancient ruins", "Mysterious forest", "Futuristic city"])
    
    # ১. টেক্সট জেনারেশন
    chat_resp = client.chat_completion(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": f"Write a short Bengali caption about {topic}. Add hashtags."}]
    )
    caption = chat_resp.choices[0].message.content.strip()

    # ২. ইমেজ জেনারেশন
    image = client.text_to_image(prompt=topic, model=IMAGE_MODEL)
    buf = io.BytesIO()
    image.convert("RGB").resize((1080, 1080)).save(buf, format="JPEG", quality=90)
    
    return buf.getvalue(), caption

def post_to_facebook(image_bytes, caption, fb_token, page_id):
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    # 'published': 'true' নিশ্চিত করে পোস্টটি ড্রাফটে না রেখে সরাসরি পাবলিশ করবে
    data = {
        "message": caption, 
        "access_token": fb_token,
        "published": "true" 
    }
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    
    try:
        resp = requests.post(url, data=data, files=files)
        result = resp.json()
        
        # ফেসবুকের আসল রেসপন্স লগে দেখা যাবে
        logger.info(f"Facebook API Response: {result}")
        
        if "id" in result:
            return True, result["id"]
        else:
            return False, result
    except Exception as e:
        return False, str(e)

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")

    if not all([fb_token, page_id, hf_token]):
        logger.error("Environment variables missing!")
        return

    try:
        img_data, caption = generate_content(hf_token)
        success, info = post_to_facebook(img_data, caption, fb_token, page_id)
        
        if success:
            logger.info(f"Successfully posted! ID: {info}")
        else:
            logger.error(f"Facebook post failed: {info}")
            
    except Exception as e:
        logger.error(f"Error in main: {e}")

if __name__ == "__main__":
    main()

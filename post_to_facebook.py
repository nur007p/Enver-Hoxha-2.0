import os
import random
import io
import logging
import requests
from huggingface_hub import InferenceClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_content(hf_token):
    # সবচাইতে নির্ভরযোগ্য ফ্রি মডেল এবং এন্ডপয়েন্ট
    client = InferenceClient(api_key=hf_token)
    
    # বিষয়বস্তু নির্বাচন
    topics = ["Ancient ruins in a misty forest", "A futuristic cyberpunk city", "A serene traditional village"]
    topic = random.choice(topics)

    # ১. টেক্সট জেনারেশন (সহজ উপায়ে)
    text_model = "Qwen/Qwen2.5-72B-Instruct"
    chat_resp = client.chat_completion(
        model=text_model,
        messages=[{"role": "user", "content": f"Write a 3-sentence Bengali caption about {topic}. Add hashtags."}]
    )
    caption = chat_resp.choices[0].message.content.strip()

    # ২. ইমেজ জেনারেশন (সবচেয়ে স্টেবল ফ্রি মডেল)
    image_model = "runwayml/stable-diffusion-v1-5"
    image = client.text_to_image(prompt=topic, model=image_model)
    
    buf = io.BytesIO()
    image.convert("RGB").resize((1080, 1080)).save(buf, format="JPEG")
    return buf.getvalue(), caption

def post_to_facebook(image_bytes, caption, fb_token, page_id):
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    data = {"message": caption, "access_token": fb_token}
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    
    resp = requests.post(url, data=data, files=files)
    if resp.status_code == 200:
        logger.info("পাবলিশ হয়েছে!")
        return True
    else:
        logger.error(f"ফেসবুক এরর: {resp.text}")
        return False

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")

    if not all([fb_token, page_id, hf_token]):
        logger.error("টোকেন বা আইডি মিসিং!")
        return

    try:
        img_data, caption = generate_content(hf_token)
        post_to_facebook(img_data, caption, fb_token, page_id)
    except Exception as e:
        logger.error(f"মেইন ফাংশন এরর: {e}")

if __name__ == "__main__":
    main()

import os
import random
import io
import logging
import requests
from huggingface_hub import InferenceClient

# লগের ফরম্যাট সেটআপ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ফ্রি টায়ারের উপযোগী মডেল
TEXT_MODEL = "Qwen/Qwen2.5-72B-Instruct" 
IMAGE_MODEL = "stabilityai/stable-diffusion-2-1"

def generate_content(hf_token):
    # api_key ব্যবহার করা ভালো প্র্যাকটিস
    client = InferenceClient(api_key=hf_token)
    topics = ["Ancient ruins", "Mysterious forest", "Futuristic city"]
    topic = random.choice(topics)

    # টেক্সট জেনারেশন
    chat_resp = client.chat_completion(
        model=TEXT_MODEL,
        messages=[{"role": "user", "content": f"Write a short Bengali caption about {topic}. Add 3 hashtags."}]
    )
    caption = chat_resp.choices[0].message.content.strip()

    # ইমেজ জেনারেশন
    image = client.text_to_image(prompt=topic, model=IMAGE_MODEL)
    
    # মেমোরিতে ইমেজ সেভ করা
    buf = io.BytesIO()
    image.convert("RGB").resize((1024, 1024)).save(buf, format="JPEG")
    
    return buf.getvalue(), caption

def post_to_facebook(image_bytes, caption, fb_token, page_id):
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    data = {"message": caption, "access_token": fb_token}
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    
    resp = requests.post(url, data=data, files=files)
    return resp.status_code == 200

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")

    if not all([fb_token, page_id, hf_token]):
        logger.error("Environment variables missing.")
        return

    img_data, caption = generate_content(hf_token)
    if post_to_facebook(img_data, caption, fb_token, page_id):
        logger.info("Successfully posted!")

if __name__ == "__main__":
    main()

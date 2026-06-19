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
    topics = ["Ancient ruins in a misty forest", "A futuristic cyberpunk city", "A serene traditional village"]
    topic = random.choice(topics)

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
    # ফেসবুক গ্রাফ এপিআই এর মাধ্যমে পোস্ট করা
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    data = {
        "message": caption,
        "access_token": fb_token,
        "published": "true" # নিশ্চিত করা হচ্ছে পোস্টটি পাবলিশ হবে
    }
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    
    resp = requests.post(url, data=data, files=files)
    result = resp.json()
    
    # ফেসবুকের আসল রিপ্লাই লগ করা
    logger.info(f"ফেসবুক এপিআই রেসপন্স: {result}")
    
    if "id" in result:
        return True, result["id"]
    return False, result

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")

    if not all([fb_token, page_id, hf_token]):
        logger.error("এনভায়রনমেন্ট ভেরিয়েবল মিসিং!")
        return

    try:
        img_data, caption = generate_content(hf_token)
        success, post_id = post_to_facebook(img_data, caption, fb_token, page_id)
        
        if success:
            logger.info(f"সফলভাবে পোস্ট করা হয়েছে! পোস্ট আইডি: {post_id}")
        else:
            logger.error(f"পোস্ট করা যায়নি। ফেসবুকের এরর: {post_id}")
    except Exception as e:
        logger.error(f"কোডে এরর: {e}")

if __name__ == "__main__":
    main()

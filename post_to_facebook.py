import os
import random
import sys
import logging
import requests
import google.generativeai as genai

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Gemini কনফিগারেশন
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# মডেল আপডেট: gemini-1.5-flash-latest ব্যবহার করুন
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def get_gemini_content(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        return "এক চমৎকার রহস্যময় দৃশ্য।"

def generate_image_and_data():
    # র্যান্ডম টপিক
    topics = [
        "Futuristic Dhaka city in 2070", 
        "A hidden village in the Himalayas",
        "A mystical forest in the Sundarbans", 
        "Cyberpunk rickshaw in rainy street"
    ]
    topic = random.choice(topics)
    
    # ক্যাপশন তৈরি (Gemini দিয়ে)
    caption_prompt = f"Write an engaging Facebook caption in Bengali about: {topic}. Keep it short and add 4 relevant hashtags."
    caption = get_gemini_content(caption_prompt)
    
    # ইমেজ জেনারেশন (Pollinations.ai দিয়ে)
    # প্রম্পটটি URL এনকোড করা জরুরি
    safe_prompt = requests.utils.quote(f"Professional cinematic art of {topic}")
    image_url = f"https://pollinations.ai/p/{safe_prompt}?width=1024&height=768&nologo=true&seed={random.randint(1, 10000)}"
    
    logger.info(f"Downloading image from: {image_url}")
    image_response = requests.get(image_url, timeout=60)
    
    if image_response.status_code == 200:
        return image_response.content, caption
    else:
        raise Exception(f"Failed to generate image: {image_response.status_code}")

def post_to_facebook(image_bytes, caption, token, page_id):
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    
    # ফাইল আপলোডের জন্য সঠিক ফরম্যাট
    files = {
        'source': ('image.jpg', image_bytes, 'image/jpeg')
    }
    data = {
        'message': caption,
        'access_token': token
    }
    
    logger.info("Uploading to Facebook...")
    response = requests.post(url, files=files, data=data, timeout=90)
    result = response.json()
    
    if "id" in result:
        logger.info(f"Successfully posted! Post ID: {result['id']}")
        return True
    else:
        logger.error(f"Facebook API Error: {result}")
        return False

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    fb_page_id = os.environ.get("FB_PAGE_ID")
    
    if not all([fb_token, fb_page_id, os.environ.get("GEMINI_API_KEY")]):
        logger.error("Missing Environment Variables!")
        sys.exit(1)

    try:
        img_bytes, caption = generate_image_and_data()
        if not post_to_facebook(img_bytes, caption, fb_token, fb_page_id):
            sys.exit(1)
    except Exception as e:
        logger.error(f"Process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

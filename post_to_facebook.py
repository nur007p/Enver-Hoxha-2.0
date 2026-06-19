import os
import random
import sys
import logging
import requests
import google.generativeai as genai

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FB_GRAPH_API = "https://graph.facebook.com/v21.0"

# Gemini কনফিগারেশন
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def get_gemini_content(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return "এক চমৎকার রহস্যময় দৃশ্য।"

def generate_image_and_data():
    topic = random.choice([
        "Futuristic Dhaka city in 2070", "A hidden village in the Himalayas",
        "A mystical forest in the Sundarbans", "Cyberpunk rickshaw in rainy street"
    ])
    
    # ক্যাপশন তৈরি
    caption = get_gemini_content(f"Write an engaging Facebook caption in Bengali about: {topic}. Keep it short and add 4 relevant hashtags.")
    
    # ইমেজ জেনারেশন (Pollinations.ai)
    safe_prompt = requests.utils.quote(f"High quality, cinematic, {topic}")
    image_url = f"https://pollinations.ai/p/{safe_prompt}?width=1024&height=768&nologo=true&seed={random.randint(1, 10000)}"
    
    image_response = requests.get(image_url)
    return image_response.content, caption

def post_to_facebook(image_bytes, caption, token, page_id):
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    files = {
        "source": ("image.jpg", image_bytes, "image/jpeg"),
        "message": (None, caption)
    }
    data = {"access_token": token}
    
    resp = requests.post(url, data=data, files=files)
    result = resp.json()
    
    if "id" in result:
        logger.info(f"Successfully posted! ID: {result['id']}")
        return True
    else:
        logger.error(f"Facebook API Error: {result}")
        return False

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    fb_page_id = os.environ.get("FB_PAGE_ID")
    
    if not all([fb_token, fb_page_id]):
        logger.error("Environment variables missing.")
        sys.exit(1)

    img_bytes, caption = generate_image_and_data()
    if not post_to_facebook(img_bytes, caption, fb_token, fb_page_id):
        sys.exit(1)

if __name__ == "__main__":
    main()

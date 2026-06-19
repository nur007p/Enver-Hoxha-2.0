import os
import requests
import logging
from google import genai

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# নতুন google-genai ক্লায়েন্ট সেটআপ
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_caption():
    try:
        # মডেল: gemini-1.5-flash
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents="Write a short engaging Bengali Facebook caption for a futuristic city. Add 3 hashtags.",
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        return "ভবিষ্যতের ঢাকা শহর! #FuturisticDhaka #AI #Technology"

def post_to_facebook(caption):
    # ইমেজ ডাউনলোড (Pollinations.ai)
    image_url = "https://pollinations.ai/p/futuristic_dhaka_2070?width=1024&height=768&nologo=true"
    img_response = requests.get(image_url, timeout=60)
    
    if img_response.status_code != 200:
        logger.error("Image download failed")
        return

    # ফাইল হিসেবে সেভ করা (ফেসবুক এরর সমাধানের জন্য অপরিহার্য)
    with open("image.jpg", "wb") as f:
        f.write(img_response.content)

    # ফেসবুক গ্রাফ এপিআই (v21.0)
    url = f"https://graph.facebook.com/v21.0/{os.environ.get('FB_PAGE_ID')}/photos"
    
    with open("image.jpg", "rb") as f:
        # ফেসবুকের জন্য multipart/form-data ফরম্যাট
        files = {
            'source': ('image.jpg', f, 'image/jpeg')
        }
        data = {
            'message': caption,
            'access_token': os.environ.get('FB_PAGE_TOKEN'),
            'published': 'true'
        }
        
        response = requests.post(url, files=files, data=data)
        result = response.json()
        
    logger.info(f"Facebook response: {result}")
        
    # কাজ শেষ হলে ফাইল ডিলিট
    if os.path.exists("image.jpg"):
        os.remove("image.jpg")

if __name__ == "__main__":
    caption = generate_caption()
    post_to_facebook(caption)

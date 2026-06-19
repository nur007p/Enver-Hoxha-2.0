import os
import requests
import logging
from google import genai

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ক্লায়েন্ট সেটআপ
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_caption():
    try:
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents="Write a short engaging Bengali Facebook caption for a futuristic city. Add 3 hashtags.",
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        return "ভবিষ্যতের শহর! #Dhaka #AI #Future"

def post_to_facebook(caption):
    # ১. ইমেজ ডাউনলোড
    image_url = "https://pollinations.ai/p/futuristic_dhaka_city?width=1024&height=768&nologo=true"
    img_response = requests.get(image_url, timeout=60)
    
    if img_response.status_code != 200:
        logger.error("Image download failed")
        return

    # ২. ফাইল সেভ করা (লোকাল ফাইল হিসেবে)
    with open("image.jpg", "wb") as f:
        f.write(img_response.content)

    # ৩. ফেসবুক এপিআই আপলোড
    url = f"https://graph.facebook.com/v21.0/{os.environ.get('FB_PAGE_ID')}/photos"
    
    # টোকেন ও ডাটা
    params = {
        'access_token': os.environ.get('FB_PAGE_TOKEN'),
        'message': caption,
        'published': 'true'
    }

    with open("image.jpg", "rb") as f:
        files = {'source': f}
        # params আলাদাভাবে পাঠানো হচ্ছে
        response = requests.post(url, data=params, files=files)
        
    result = response.json()
    logger.info(f"Facebook response: {result}")
        
    # ফাইল মুছে ফেলা
    if os.path.exists("image.jpg"):
        os.remove("image.jpg")

if __name__ == "__main__":
    caption = generate_caption()
    post_to_facebook(caption)

import os
import requests
import logging
from google import genai  # নতুন লাইব্রেরি
from google.genai import types

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# নতুন এসডিকে (SDK) দিয়ে ক্লায়েন্ট তৈরি
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_caption():
    # নতুন মডেল ব্যবহার (gemini-2.0-flash বা gemini-1.5-flash)
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents="Write a short engaging Bengali Facebook caption for a futuristic city. Add 3 hashtags.",
    )
    return response.text

def post_to_facebook(caption):
    # ইমেজ ডাউনলোড ও লোকাল ফাইলে সেভ করা (ফেসবুকের এরর সমাধানের জন্য)
    image_url = "https://pollinations.ai/p/futuristic_city_2070?width=1024&height=768&nologo=true"
    img_response = requests.get(image_url)
    
    with open("image.jpg", "wb") as f:
        f.write(img_response.content)

    # ফেসবুক এপিআই আপলোড
    url = f"https://graph.facebook.com/v21.0/{os.environ.get('FB_PAGE_ID')}/photos"
    
    with open("image.jpg", "rb") as f:
        files = {'source': f}
        data = {
            'message': caption,
            'access_token': os.environ.get('FB_PAGE_TOKEN')
        }
        response = requests.post(url, files=files, data=data)
    
    logger.info(f"Facebook response: {response.json()}")

if __name__ == "__main__":
    caption = generate_caption()
    post_to_facebook(caption)

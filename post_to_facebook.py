import os
import random
import logging
import requests
import google.generativeai as genai

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Gemini কনফিগারেশন
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def get_gemini_content(prompt: str) -> str:
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        return "এক চমৎকার রহস্যময় দৃশ্য।"

def generate_image_and_data():
    topics = ["Futuristic Dhaka city in 2070", "A mystical forest in the Sundarbans"]
    topic = random.choice(topics)
    
    caption = get_gemini_content(f"Write a short Bengali caption for: {topic}. Add 3 hashtags.")
    
    # ইমেজ ডাউনলোড ও সেভ করা
    safe_prompt = requests.utils.quote(f"Cinematic art of {topic}")
    image_url = f"https://pollinations.ai/p/{safe_prompt}?width=1024&height=768&nologo=true"
    
    response = requests.get(image_url, timeout=60)
    if response.status_code == 200:
        # ফাইল হিসেবে সেভ করা
        with open("temp_image.jpg", "wb") as f:
            f.write(response.content)
        return "temp_image.jpg", caption
    else:
        raise Exception("Image download failed")

def post_to_facebook(image_path, caption, token, page_id):
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    
    # ফাইলটি ওপেন করে পাঠানো
    with open(image_path, 'rb') as f:
        files = {'source': f}
        data = {
            'message': caption,
            'access_token': token
        }
        
        response = requests.post(url, files=files, data=data)
        result = response.json()
    
    # কাজ শেষ হলে টেম্পোরারি ফাইলটি ডিলিট করে দেওয়া
    if os.path.exists(image_path):
        os.remove(image_path)
    
    if "id" in result:
        logger.info(f"Success! ID: {result['id']}")
        return True
    else:
        logger.error(f"Facebook API Error: {result}")
        return False

def main():
    try:
        image_path, caption = generate_image_and_data()
        post_to_facebook(image_path, caption, os.environ.get("FB_PAGE_TOKEN"), os.environ.get("FB_PAGE_ID"))
    except Exception as e:
        logger.error(f"Main execution failed: {e}")

if __name__ == "__main__":
    main()

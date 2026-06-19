import os
import random
import sys
import logging
import requests
import google.generativeai as genai

# লগের ফরম্যাট সেটআপ
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
        return ""

def generate_image_and_data():
    # র্যান্ডম টপিক
    topic = "A futuristic Bengali village in 2050" 
    
    # ক্যাপশন তৈরি
    caption = get_gemini_content(f"Write a short, engaging Facebook caption in Bengali about: {topic}. End with 4 hashtags.")
    
    # ইমেজ জেনারেশন (Pollinations.ai ব্যবহার করে)
    safe_prompt = requests.utils.quote(f"Professional photography of {topic}")
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
    return "id" in result

def main():
    if not post_to_facebook(*generate_image_and_data(), os.environ.get("FB_PAGE_TOKEN"), os.environ.get("FB_PAGE_ID")):
        sys.exit(1)

if __name__ == "__main__":
    main()

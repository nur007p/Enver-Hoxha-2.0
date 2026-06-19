import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def post_to_facebook():
    # গিটহাব থেকে সিক্রেটস নিন
    page_id = os.environ.get("FB_PAGE_ID")
    page_token = os.environ.get("FB_PAGE_TOKEN") # এখন এখানে Page Access Token থাকবে

    # ছবি ডাউনলোড
    image_url = "https://pollinations.ai/p/Futuristic_Dhaka_City_2070?width=1024&height=768&nologo=true"
    response = requests.get(image_url, timeout=60)
    with open("image.jpg", "wb") as f:
        f.write(response.content)

    # ফেসবুক পেজ ফটো এপিআই
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    
    with open("image.jpg", "rb") as f:
        data = {
            'message': "ভবিষ্যতের ঢাকা শহর! #Dhaka #AI",
            'access_token': page_token, # নতুন পেজ টোকেন
            'published': 'true'
        }
        files = {'source': f}
        
        # পোস্ট রিকোয়েস্ট
        resp = requests.post(url, data=data, files=files)
        logger.info(f"Facebook response: {resp.json()}")

    if os.path.exists("image.jpg"):
        os.remove("image.jpg")

if __name__ == "__main__":
    post_to_facebook()

import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def post_to_facebook():
    page_id = os.environ.get("FB_PAGE_ID")
    page_token = os.environ.get("FB_PAGE_TOKEN")

    # ছবি ডাউনলোড
    img_url = "https://pollinations.ai/p/Futuristic_Dhaka_City_2070?width=1024&height=768&nologo=true"
    response = requests.get(img_url)
    with open("image.jpg", "wb") as f:
        f.write(response.content)

    # নতুন ভার্সনে পোস্ট করার নিয়ম
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    
    with open("image.jpg", "rb") as f:
        # এখানে 'published': 'true' নিশ্চিত করতে হবে
        payload = {
            'message': 'ভবিষ্যতের ঢাকা শহর! #Dhaka2070',
            'access_token': page_token,
            'published': 'true' 
        }
        files = {'source': f}
        
        # পোস্ট রিকোয়েস্ট
        resp = requests.post(url, data=payload, files=files)
        logger.info(f"Facebook Result: {resp.json()}")

    if os.path.exists("image.jpg"):
        os.remove("image.jpg")

if __name__ == "__main__":
    post_to_facebook()

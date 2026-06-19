import os
import requests
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def post_to_facebook():
    # ফেসবুক ক্রেডেন্সিয়াল সিক্রেট থেকে লোড করা হচ্ছে
    page_id = os.environ.get("FB_PAGE_ID")
    token = os.environ.get("FB_PAGE_TOKEN")

    if not page_id or not token:
        logger.error("Facebook ID অথবা Token পাওয়া যায়নি!")
        return

    # ১. ছবি ডাউনলোড
    image_url = "https://pollinations.ai/p/Futuristic_Dhaka_City_2070?width=1024&height=768&nologo=true"
    response = requests.get(image_url, timeout=60)
    
    if response.status_code == 200:
        with open("image.jpg", "wb") as f:
            f.write(response.content)
    else:
        logger.error("ছবি ডাউনলোড ব্যর্থ হয়েছে।")
        return

    # ২. ফেসবুক এপিআই-তে পোস্ট করা
    url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
    
    with open("image.jpg", "rb") as f:
        data = {
            'message': "ভবিষ্যতের ঢাকা শহর! #FuturisticDhaka #AI #Technology",
            'access_token': token,
            'published': 'true'
        }
        files = {'source': f}
        
        resp = requests.post(url, data=data, files=files)
        result = resp.json()
        
    # ফলাফল লগ করা
    if "id" in result:
        logger.info(f"সফলভাবে পোস্ট হয়েছে! পোস্ট ID: {result['id']}")
    else:
        logger.error(f"ফেসবুক এরর: {result}")

    # ৩. টেম্পোরারি ফাইল মুছে ফেলা
    if os.path.exists("image.jpg"):
        os.remove("image.jpg")

if __name__ == "__main__":
    post_to_facebook()

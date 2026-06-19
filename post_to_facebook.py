import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def post_to_facebook():
    # ১. ক্যাপশন ও ছবির জন্য প্রম্পট
    topic = "Futuristic Dhaka city in 2070"
    
    # ২. ছবি ডাউনলোড (Pollinations.ai)
    image_url = f"https://pollinations.ai/p/{topic.replace(' ', '_')}?width=1024&height=768&nologo=true"
    img_response = requests.get(image_url)
    
    with open("image.jpg", "wb") as f:
        f.write(img_response.content)

    # ৩. ফেসবুক এপিআই আপলোড
    url = f"https://graph.facebook.com/v21.0/{os.environ.get('FB_PAGE_ID')}/photos"
    
    with open("image.jpg", "rb") as f:
        files = {'source': ('image.jpg', f, 'image/jpeg')}
        data = {
            'message': f"ভবিষ্যতের ঢাকা শহর! এই ছবিটি কৃত্রিম বুদ্ধিমত্তা দ্বারা তৈরি। #Dhaka2070 #AI #Future",
            'access_token': os.environ.get('FB_PAGE_TOKEN'),
            'published': 'true'
        }
        
        response = requests.post(url, files=files, data=data)
        result = response.json()
        logger.info(f"Facebook response: {result}")
        
    if os.path.exists("image.jpg"):
        os.remove("image.jpg")

if __name__ == "__main__":
    post_to_facebook()

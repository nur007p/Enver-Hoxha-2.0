import os
import random
import sys
import io
import logging
import requests
from huggingface_hub import InferenceClient
from PIL import Image, ImageDraw, ImageFont

# লগের ফরম্যাট সেটআপ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FB_GRAPH_API = "https://graph.facebook.com/v21.0"
TARGET_IMAGE_SIZE = (1080, 1920) # ইনস্টাগ্রাম ও ফেসবুক রিল/পোস্টের জন্য ৯:১৬ রেশিও

TEXT_MODELS = ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.1-70B-Instruct"]
IMAGE_MODEL = "runwayml/stable-diffusion-v1-5" # ফ্রি মডেল

TOPIC_CATEGORIES = [
    "Ancient Lost Civilization in the Amazon", "Mysterious Historical Event from 19th Century",
    "Architectural Wonder of a Lost Empire", "Medieval Secret Castle in the Alps",
    "Forgotten Treasure in a dense Jungle", "Secret Passage in an Egyptian Pyramid",
    "Futuristic Cyberpunk Cityscape at Night", "Floating Islands in the Sky",
    "Bioluminescent Enchanted Forest", "Ethereal Spirit of the Sundarbans Mangrove",
    "Haunted Lighthouse on a Rocky Cliff", "A Waterfall Flowing into the Void"
]

def build_client(hf_token: str) -> InferenceClient:
    return InferenceClient(token=hf_token)

def get_hf_text(client: InferenceClient, instruction: str) -> str:
    try:
        response = client.chat_completion(
            model=TEXT_MODELS[0],
            messages=[{"role": "user", "content": instruction}],
            max_tokens=300,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Text generation failed: {e}")
        return "রহস্যময় এই দৃশ্যটি আপনার কল্পনাকে রাঙিয়ে তুলুক।"

def generate_image_and_data(client: InferenceClient):
    topic = random.choice(TOPIC_CATEGORIES)
    
    # প্রম্পট জেনারেশন
    prompt = f"High-quality cinematic wide shot of {topic}, mysterious atmosphere, 8k resolution, photorealistic."
    
    # ক্যাপশন জেনারেশন (হ্যাশট্যাগসহ)
    caption_instr = f"Write a short, engaging Bengali storytelling caption about '{topic}'. Include 4-5 relevant hashtags."
    caption = get_hf_text(client, caption_instr)
    
    # ইমেজ জেনারেশন
    try:
        raw = client.text_to_image(prompt, model=IMAGE_MODEL)
        img = raw if isinstance(raw, Image.Image) else Image.open(io.BytesIO(raw))
        
        # রিসাইজ করা (৯:১৬ রেশিও)
        img = img.convert("RGB").resize(TARGET_IMAGE_SIZE, Image.LANCZOS)
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue(), caption
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise RuntimeError("Image generation failed.")

def post_to_facebook(image_bytes, caption, token, page_id):
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    data = {"message": caption, "access_token": token}
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    
    resp = requests.post(url, data=data, files=files)
    return resp.json()

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    fb_page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")
    
    if not all([fb_token, fb_page_id, hf_token]):
        logger.error("Missing credentials.")
        sys.exit(1)

    client = build_client(hf_token)
    img_bytes, caption = generate_image_and_data(client)
    post_to_facebook(img_bytes, caption, fb_token, fb_page_id)
    logger.info("Posted successfully!")

if __name__ == "__main__":
    main()

import os
import random
import sys
import io
import logging
import requests
from huggingface_hub import InferenceClient
from PIL import Image

# লগের ফরম্যাট সেটআপ
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FB_GRAPH_API = "https://graph.facebook.com/v21.0"
TARGET_IMAGE_SIZE = (1024, 768)

TEXT_MODELS = ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.1-70B-Instruct"]
IMAGE_MODELS = ["black-forest-labs/FLUX.1-schnell", "black-forest-labs/FLUX.1-dev"]

# ৫০টি টপিকের তালিকা
TOPIC_CATEGORIES = [
    "Ancient Lost Civilization in the Amazon", "Mysterious Historical Event from 19th Century",
    "Architectural Wonder of a Lost Empire", "Mythological Kingdom Under the Sea",
    "Medieval Secret Castle in the Alps", "Historical Underwater Ruins of Dwarka",
    "Unsolved Historical Mystery of the Voynich Manuscript", "Ancient Scientific Innovation of the Mayans",
    "Forgotten Treasure in a dense Jungle", "Secret Passage in an Egyptian Pyramid",
    "Lost City of Gold in the Andes", "Ghostly Legend of a Forgotten Palace",
    "Futuristic Cyberpunk Cityscape at Night", "Deep Space Exploration Wonder",
    "Surreal Steampunk Laboratory", "Nature-infused Fantasy Village",
    "Floating Islands in the Sky", "Bioluminescent Enchanted Forest",
    "Conceptual Art of Time Travel Mechanism", "Cybernetic Samurai in a Bamboo Forest",
    "Colony on a Distant Exoplanet", "Hidden Doorway to a Parallel Universe",
    "Floating City of Alchemists", "Neon-lit Forest with Ethereal Wildlife",
    "Crystal Palace in an Alien Landscape", "Robot Gardener in a Post-Apocalyptic World",
    "Traditional Bengali Village Life during Harvest", "Majestic Wildlife in Wild Habitat",
    "Ethereal Spirit of the Sundarbans Mangrove", "Mystical Village Fair under a Full Moon",
    "Traditional Boat Race on a Stormy River", "Haunted Lighthouse on a Rocky Cliff",
    "A Waterfall Flowing into the Void", "Cursed Treasure in a Deep Cave",
    "Sunset over a Futuristic Himalayan Village", "Mythical Sea Serpent in the Bay of Bengal",
    "Ancient Library Protected by Magical Creatures", "Golden Rice Fields of Rural Bengal",
    "Rainy Afternoon in a Traditional Bengali House", "Firefly Gathering in an Ancient Banyan Tree",
    "A Clockwork City inside a Giant Glass Sphere", "Library of Lost Knowledge in a Desert",
    "A Tree that grows Stars instead of Leaves", "Ancient Bengali Folklore Creature in a Modern Setting",
    "A Bridge connecting two Moons", "Stairway to the Clouds in a Mountain Peak",
    "Abandoned Train Station in a Haunted Forest", "Spirit of the Wind in a Winter Valley",
    "Deserted Carnival with Eerie Decorations", "A Kingdom made entirely of Stained Glass"
]

def build_client(hf_token: str) -> InferenceClient:
    return InferenceClient(token=hf_token)

def get_hf_text(client: InferenceClient, instruction: str, max_tokens: int = 800) -> str:
    for model in TEXT_MODELS:
        try:
            response = client.chat_completion(
                model=model,
                messages=[{"role": "user", "content": instruction}],
                max_tokens=max_tokens,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
    return "রহস্যময় এই দৃশ্যটি আপনার কল্পনাকে রাঙিয়ে তুলুক।"

def generate_image_and_data(client: InferenceClient):
    topic = random.choice(TOPIC_CATEGORIES)
    
    # প্রম্পট জেনারেশন
    prompt_instr = f"Create a descriptive, high-quality AI image prompt for: '{topic}'. Output ONLY the prompt."
    prompt = get_hf_text(client, prompt_instr, max_tokens=150)
    
    # ক্যাপশন জেনারেশন
    caption_instr = (
        f"Image Subject: '{prompt}'. "
        "Write a natural, storytelling-style Facebook caption in Bengali. "
        "Rules: 1. Start with a hook. 2. Describe the scene vividly without using robotic or difficult words. "
        "3. Keep it within 3-4 short, flowing sentences. "
        "4. End with 4-5 relevant hashtags. "
        "IMPORTANT: The response MUST be complete. Do not truncate the end of the text."
    )
    caption = get_hf_text(client, caption_instr, max_tokens=400)
    
    # ইমেজ জেনারেশন
    for model in IMAGE_MODELS:
        try:
            raw = client.text_to_image(prompt, model=model)
            img = raw if isinstance(raw, Image.Image) else Image.open(io.BytesIO(raw))
            buf = io.BytesIO()
            img.convert("RGB").resize(TARGET_IMAGE_SIZE, Image.LANCZOS).save(buf, format="JPEG", quality=90)
            return buf.getvalue(), caption
        except Exception:
            continue
    raise RuntimeError("Image generation failed.")

def post_to_facebook(image_bytes, caption, token, page_id):
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    
    # সঠিক ফরম্যাট: data এবং files আলাদা প্যারামিটার হিসেবে যাবে
    data = {"message": caption, "access_token": token}
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    
    try:
        resp = requests.post(url, data=data, files=files, timeout=90)
        result = resp.json()
        if "id" in result:
            logger.info(f"Successfully posted! ID: {result['id']}")
            return True
        else:
            logger.error(f"Facebook API Error: {result}")
            return False
    except Exception as e:
        logger.error(f"Posting failed: {e}")
        return False

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    fb_page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")
    
    if not all([fb_token, fb_page_id, hf_token]):
        logger.error("Environment variables missing.")
        sys.exit(1)

    client = build_client(hf_token)
    img_bytes, caption = generate_image_and_data(client)
    
    if not post_to_facebook(img_bytes, caption, fb_token, fb_page_id):
        sys.exit(1)

if __name__ == "__main__":
    main()

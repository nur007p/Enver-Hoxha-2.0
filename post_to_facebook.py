"""
Auto Facebook Poster & Reels Generator
- প্রতি ৩০ মিনিটে ছবি পোস্ট
- প্রতি ৬ষ্ঠ রান-এ রিলস আপলোড (প্রতি ৩ ঘণ্টা)
"""

import os
import random
import sys
import time
import io
import logging
import requests
from huggingface_hub import InferenceClient
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

FB_GRAPH_API = "https://graph.facebook.com/v21.0"
TARGET_IMAGE_SIZE = (1024, 768)

TEXT_MODELS = ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.1-8B-Instruct"]
IMAGE_MODELS = ["black-forest-labs/FLUX.1-schnell", "black-forest-labs/FLUX.1-dev"]

# আপনার ২০টি ক্যাটাগরি
TOPIC_CATEGORIES = [
    "Ancient Lost Civilization", "Mysterious Historical Event",
    "Architectural Wonder of the Past", "Mythological Kingdom",
    "Medieval Secret Castle", "Historical Underwater Ruins",
    "Futuristic Cyberpunk Cityscape", "Deep Space Exploration Wonder",
    "Surreal Steampunk Laboratory", "Nature-infused Fantasy Village",
    "Unsolved Historical Mystery", "Traditional Bengali Village Life",
    "Ancient Scientific Innovation", "Nature's Hidden Paradise",
    "Majestic Wildlife in Wild Habitat", "Floating Islands in the Sky",
    "Forgotten Treasure in a Jungle", "Bioluminescent Enchanted Forest",
    "Intergalactic Trading Space Station", "Zen Temple on a Misty Mountain"
]

def create_reel(image_bytes: bytes, audio_path: str = "bg_music.mp3") -> str:
    """ছবি থেকে ১০ সেকেন্ডের ভিডিও রিলস তৈরি করে"""
    output_path = "output_reel.mp4"
    image = Image.open(io.BytesIO(image_bytes))
    image.save("temp_frame.jpg")
    
    # ১০ সেকেন্ডের ক্লিপ এবং অডিও সেট করা
    clip = ImageClip("temp_frame.jpg").set_duration(10)
    audio = AudioFileClip(audio_path).subclip(0, 10) 
    video = clip.set_audio(audio)
    
    video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    return output_path

def post_video_to_facebook(video_path: str, caption: str, token: str, page_id: str):
    """ভিডিও বা রিলস পোস্ট করার ফাংশন"""
    url = f"{FB_GRAPH_API}/{page_id}/videos"
    with open(video_path, 'rb') as f:
        files = {'source': f}
        data = {'description': caption, 'access_token': token}
        requests.post(url, data=data, files=files)

def post_to_facebook(image_bytes: bytes, caption: str, token: str, page_id: str):
    """ছবি পোস্ট করার ফাংশন"""
    url = f"{FB_GRAPH_API}/{page_id}/photos"
    files = {"source": ("image.jpg", image_bytes, "image/jpeg")}
    data = {"message": caption, "access_token": token}
    requests.post(url, data=data, files=files)

# (বাকি ফাংশনগুলো যেমন: get_hf_text, auto_generate_topic, generate_prompt, generate_caption একই থাকবে)

def main():
    fb_token = os.environ.get("FB_PAGE_TOKEN")
    fb_page_id = os.environ.get("FB_PAGE_ID")
    hf_token = os.environ.get("HF_TOKEN")
    
    # রান কাউন্টার ম্যানেজমেন্ট
    counter_file = "run_counter.txt"
    count = 0
    if os.path.exists(counter_file):
        with open(counter_file, "r") as f:
            count = int(f.read())
    
    count = (count + 1) % 6
    with open(counter_file, "w") as f:
        f.write(str(count))

    # মূল লজিক
    client = InferenceClient(token=hf_token)
    topic = auto_generate_topic(client)
    prompt = generate_prompt(client, topic, "")
    caption = generate_caption(client, prompt)
    img_bytes = generate_image_hf(client, prompt)
    
    if count == 0:
        logger.info("রিলস জেনারেশন মোড...")
        video_path = create_reel(img_bytes)
        post_video_to_facebook(video_path, caption, fb_token, fb_page_id)
    else:
        post_to_facebook(img_bytes, caption, fb_token, fb_page_id)

if __name__ == "__main__":
    main()

import os
import random
import glob
import io
import logging
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip

# আপনার আগের কোডের সব ইমপোর্ট এবং কনফিগারেশন এখানে থাকবে...

def get_random_audio(folder_path="music/*.mp3"):
    """music ফোল্ডার থেকে র‍্যান্ডমলি একটি অডিও ফাইল বেছে নেয়"""
    audio_files = glob.glob(folder_path)
    if not audio_files:
        # যদি ফোল্ডার খালি থাকে, ডিফল্ট ফাইলটি নেবে
        return "bg_music.mp3" 
    return random.choice(audio_files)

def create_reel(image_bytes: bytes) -> str:
    """ছবি থেকে ১০ সেকেন্ডের ভিডিও রিলস তৈরি করে (র‍্যান্ডম মিউজিক সহ)"""
    output_path = "output_reel.mp4"
    image = Image.open(io.BytesIO(image_bytes))
    image.save("temp_frame.jpg")
    
    # র‍্যান্ডম মিউজিক নেওয়া হচ্ছে
    audio_path = get_random_audio() 
    
    # ১০ সেকেন্ডের ক্লিপ এবং অডিও সেট করা
    clip = ImageClip("temp_frame.jpg").set_duration(10)
    audio = AudioFileClip(audio_path).subclip(0, 10) 
    video = clip.set_audio(audio)
    
    video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    return output_path

# আপনার মেইন ফাংশনের আগের অংশগুলো একই থাকবে...

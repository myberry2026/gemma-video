import requests
import base64
import json
import time
import os
from decord import VideoReader, cpu
import numpy as np
from PIL import Image
from io import BytesIO

def extract_frames_b64(video_path, num_frames=4):
    print(f"Manually extracting {num_frames} frames from {video_path}...")
    vr = VideoReader(video_path, ctx=cpu(0))
    total_frames = len(vr)
    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames = vr.get_batch(indices).asnumpy()
    
    b64_images = []
    for frame in frames:
        pil_img = Image.fromarray(frame)
        pil_img.thumbnail((800, 800))
        buffered = BytesIO()
        pil_img.save(buffered, format="JPEG", quality=85)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        b64_images.append(img_str)
    return b64_images

def run_remote_inference(video_path, prompt):
    url = "http://localhost:1234/v1/chat/completions" 
    
    images_b64 = extract_frames_b64(video_path, num_frames=4)
    
    content = []
    for img_b64 in images_b64:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{img_b64}"
            }
        })
    content.append({"type": "text", "text": prompt})
    
    payload = {
        "model": "google/gemma-4-e2b", 
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ],
        "max_tokens": 256,
        "temperature": 0.7
    }
    
    print(f"Sending 4 optimized images to {url}...")
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=60)
        if response.status_code != 200:
             print(f"API Error ({response.status_code}): {response.text}")
             return None, 0
             
        end_time = time.time()
        result = response.json()
        content = result['choices'][0]['message']['content']
        return content, end_time - start_time
    except Exception as e:
        print(f"API Error: {e}")
        return None, 0

if __name__ == "__main__":
    video_file = "real_world_traffic.mp4"
    user_prompt = "Quick check: What are the main objects in these 4 frames?"
    
    content, duration = run_remote_inference(video_file, user_prompt)
    if content:
        print("\n--- Remote Endpoint Response ---")
        print(content)
        print(f"\nStats: Total Time {duration:.1f}s")

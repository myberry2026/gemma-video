import requests
import base64
import json
import time
import os
from decord import VideoReader, cpu
import numpy as np
from PIL import Image
from io import BytesIO

def extract_frames_b64(video_path, num_frames=12):
    print(f"Manually extracting {num_frames} frames from {video_path}...")
    vr = VideoReader(video_path, ctx=cpu(0))
    total_frames = len(vr)
    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames = vr.get_batch(indices).asnumpy()
    
    b64_images = []
    for frame in frames:
        pil_img = Image.fromarray(frame)
        # Extreme optimization: Resize to 224x224
        pil_img = pil_img.resize((224, 224))
        buffered = BytesIO()
        pil_img.save(buffered, format="JPEG", quality=80)
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        b64_images.append(img_str)
    return b64_images

def run_remote_inference(video_path, prompt):
    # Switching to localhost since the IP 100.113.214.52 is the current machine
    url = "http://localhost:1234/v1/chat/completions" 
    
    # Using 12 images to stay under the 4096 token limit
    images_b64 = extract_frames_b64(video_path, num_frames=12)
    
    # Construct multi-modal message for OpenAI-compatible API
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
        "max_tokens": 512,
        "temperature": 0.7
    }
    
    print(f"Sending 16 optimized images to {url}...")
    start_time = time.time()
    try:
        response = requests.post(url, json=payload, timeout=300)
        if response.status_code != 200:
             print(f"API Error ({response.status_code}): {response.text}")
             return None, 0, 0
        
        end_time = time.time()
        result = response.json()
        content = result['choices'][0]['message']['content']
        tokens = result['usage']['completion_tokens']
        
        return content, end_time - start_time, tokens
    except Exception as e:
        print(f"API Error: {e}")
        if 'response' in locals() and response:
             print(f"Response: {response.text}")
        return None, 0, 0

if __name__ == "__main__":
    video_file = "real_world_traffic.mp4"
    user_prompt = "Perform a high-precision analysis of these 16 sequential images. Identify any fine details like brand names, specific mechanical movements, or subtle textures."
    
    content, duration, tokens = run_remote_inference(video_file, user_prompt)
    if content:
        print("\n--- Remote Endpoint Response ---")
        print(content)
        print(f"\nStats: Total Time {duration:.1f}s, Tokens {tokens} ({tokens/duration:.2f} t/s inclusive)")

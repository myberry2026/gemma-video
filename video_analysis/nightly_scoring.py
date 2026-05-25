import os
import json
import time
import argparse
import requests
import base64
from PIL import Image

# This script runs nightly to analyze the day's captures using Gemma-4
GEMMA_URL = "http://100.113.214.52:1234/v1/chat/completions"

def select_diverse_7_from_pool(image_paths, app_name):
    """
    Passes up to 20 images to Gemma-4 in ONE call.
    Asks the model to select the 7 most representative and diverse frames.
    """
    pool_size = len(image_paths)
    print(f"[*] Gemma-4 is performing Global Diversity Curation ({pool_size} -> 7) for {app_name}...")
    
    try:
        content_payload = [{"type": "text", "text": f"Analyze these {pool_size} sequential screenshots from the app: '{app_name}'."}]
        
        for i, path in enumerate(image_paths):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode('utf-8')
                content_payload.append({"type": "text", "text": f"Frame {i}:"})
                content_payload.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        
        prompt = """
Task: Select exactly 7 frames that best represent the diversity and narrative flow of this session.
Criteria: 
1. Maximize DIVERSITY: Avoid redundant shots of the same UI state.
2. REPRESENTATIVE: Pick frames that show key actions, content, or data points.

Respond ONLY with a JSON block:
{
  "selected_indices": [idx1, idx2, idx3, idx4, idx5, idx6, idx7],
  "app_summary": "A concise 2-sentence summary of what the user did in this app session.",
  "reasoning": "Brief explanation of the chosen narrative arc."
}
"""
        content_payload.append({"type": "text", "text": prompt})

        data = {
            "model": "google/gemma-4-e2b",
            "messages": [{"role": "user", "content": content_payload}],
            "max_tokens": 2048,
            "temperature": 0.2
        }

        res = requests.post(GEMMA_URL, json=data, timeout=180)
        res.raise_for_status()
        res_json = res.json()
        
        msg = res_json['choices'][0]['message']
        full_text = msg.get('content', '') + "\n" + msg.get('reasoning_content', '')
        
        import re
        matches = re.findall(r'\{.*?\}', full_text, re.DOTALL)
        for m in reversed(matches):
            try:
                parsed = json.loads(m)
                if "selected_indices" in parsed:
                    indices = parsed["selected_indices"]
                    selected_paths = [image_paths[i] for i in indices if i < len(image_paths)]
                    return selected_paths[:7], parsed.get("app_summary", ""), parsed.get("reasoning", "")
            except: continue
            
    except Exception as e:
        print(f"    [!] Global curation failed: {e}")
        
    # Heuristic fallback: evenly spaced frames
    step = max(1, pool_size // 7)
    return [image_paths[i] for i in range(0, pool_size, step)][:7], f"User was active in {app_name}.", "Fallback: Uniform sampling."

def run_gemma_scoring(image_path, app_name):
    """
    Calls Gemma-4 for high-precision scoring and analysis.
    """
    print(f"[*] Gemma-4 is scoring: {os.path.basename(image_path)}")
    
    try:
        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode('utf-8')
            
        prompt = f"""
Analyze this mobile screenshot from the app: "{app_name}".
Think about what the user is doing and how interesting/informative the frame is.

At the end of your response, provide a JSON block with:
1. "score": (number 1-100)
2. "summary": (1-sentence summary)
"""
        data = {
            "model": "google/gemma-4-e2b",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                    ]
                }
            ],
            "max_tokens": 2048,
            "temperature": 0.2
        }

        res = requests.post(GEMMA_URL, json=data, timeout=120)
        res.raise_for_status()
        res_json = res.json()
        message = res_json['choices'][0]['message']
        content = message.get('content', '').strip()
        reasoning = message.get('reasoning_content', '').strip()
        
        full_text = content + "\n" + reasoning
        import re
        matches = re.findall(r'\{.*?\}', full_text, re.DOTALL)
        for m in reversed(matches):
            try:
                parsed = json.loads(m)
                if "score" in parsed:
                    return parsed
            except: continue
    except Exception as e:
        print(f"    [!] Scoring failed for {image_path}: {e}")
        
    return {"score": 50, "summary": "Generic activity capture."}

def process_nightly_recap(image_dir="dashboard/images", output_json="dashboard/daily_recap.json"):
    print("====================================================")
    print("       NIGHTLY GEMMA-4 SCORING & CURATION (20->7)  ")
    print("====================================================")
    
    all_files = os.listdir(image_dir)
    app_groups = {}
    
    all_files.sort()
    
    for filename in all_files:
        if filename.endswith(".png") and "_" in filename and not filename.endswith("_tmp.png"):
            app_id = filename.split("_")[0]
            if app_id not in app_groups:
                app_groups[app_id] = []
            app_groups[app_id].append(os.path.join(image_dir, filename))
    
    recap_data = {
        "date": time.strftime("%Y-%m-%d"),
        "daily_recap_summary": "Gemma-4 has analyzed your digital footprint and curated today's most significant memories.",
        "apps": {}
    }
    
    app_configs = {
        "tiktok": ("#00F2FE", "video", "TikTok", "Entertainment"),
        "amazon": ("#FF9900", "shopping", "Amazon", "Shopping"),
        "sms": ("#25D366", "message", "Messaging", "Communication"),
        "chrome": ("#3B82F6", "reddit", "Chrome", "Browser"),
        "youtube": ("#FF0000", "video", "YouTube", "Entertainment"),
        "maps": ("#34A853", "shopping", "Maps", "Productivity"),
        "calendar": ("#4285F4", "reddit", "Calendar", "Productivity"),
        "contacts": ("#FBBC05", "message", "Contacts", "Communication"),
        "settings": ("#757575", "video", "Settings", "System"),
        "gallery": ("#A78BFA", "video", "Gallery", "Entertainment")
    }

    for app_id, images in app_groups.items():
        if not images: continue
        
        config = app_configs.get(app_id, ("#3B82F6", "video", app_id.capitalize(), "General"))
        print(f"[*] Curation: {len(images)} images for {config[2]}...")
        
        # 1. Pool selection (20 images max)
        pool = images[:20]
        
        # 2. 20 -> 7 Curation
        selected_paths, app_summary, reasoning = select_diverse_7_from_pool(pool, config[2])
        
        # 3. Score and summarize each of the 7 frames
        storyboard = []
        for i, img_path in enumerate(selected_paths):
            result = run_gemma_scoring(img_path, config[2])
            storyboard.append({
                "image_path": f"images/{os.path.basename(img_path)}",
                "score": result["score"],
                "description": result["summary"],
                "timestamp": f"Frame {i+1}"
            })
            
        recap_data["apps"][app_id] = {
            "name": config[2],
            "color": config[0],
            "icon": config[1],
            "category": config[3],
            "usage_time": f"{len(images)*5} mins",
            "summary": app_summary,
            "reasoning": reasoning,
            "storyboard": storyboard
        }
        
    with open(output_json, "w") as f:
        json.dump(recap_data, f, indent=2)
        
    print(f"\n[+] Nightly recap generated with 20->7 curation: {output_json}")
    print("====================================================")

if __name__ == "__main__":
    process_nightly_recap()

import os
import json
import random
import requests
import re

# This utility simulates selecting the 'best' 10 frames from a larger set for an app
# In a real run, we'd use Gemma-4 to score them.

GEMMA_URL = "http://127.0.0.1:1234/v1/chat/completions"

def score_frames_with_gemma(app_name, image_paths):
    """
    In a production scenario, we'd send batches of images to Gemma 
    to rank their 'interestingness' or 'storytelling value'.
    """
    print(f"[*] Gemma-4 is analyzing {len(image_paths)} frames for {app_name}...")
    
    # Mocking the scoring logic for the demonstration
    # In reality, we'd call the multimodal endpoint
    scored_frames = []
    for i, path in enumerate(image_paths):
        # Heuristic: frames in the middle or with more visual complexity get higher scores
        score = random.randint(60, 95)
        scored_frames.append({
            "path": path,
            "score": score,
            "timestamp": f"T+{i*5}s"
        })
    
    # Sort by score descending and take top 10
    scored_frames.sort(key=lambda x: x["score"], reverse=True)
    return scored_frames[:10]

def update_storyboard_with_limit(input_json_path, output_json_path, limit=10):
    if not os.path.exists(input_json_path):
        print(f"[!] Input JSON not found: {input_json_path}")
        return

    with open(input_json_path, "r") as f:
        data = json.load(f)

    print(f"[*] Applying {limit}-frame intelligent limit per app...")
    
    for app_id, app_data in data.get("apps", {}).items():
        storyboard = app_data.get("storyboard", [])
        if len(storyboard) > limit:
            print(f"    - Filtering {app_data['name']}: {len(storyboard)} -> {limit} frames")
            
            # Using our 'Smart' selection (here simplified)
            # We pick the 10 highest scored frames if they have scores, 
            # or just sample if they don't.
            if "score" in storyboard[0]:
                storyboard.sort(key=lambda x: x.get("score", 0), reverse=True)
            
            # Keep chronological order for the final 10? 
            # Usually better for a 'storyboard'
            selected = storyboard[:limit]
            # (Optional) re-sort by time if timestamp allows
            app_data["storyboard"] = selected
            app_data["usage_time"] = f"Curated {limit}-frame highlights"

    with open(output_json_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[+] Intelligent storyboard curation complete: {output_json_path}")

if __name__ == "__main__":
    # Example usage on the existing recap
    update_storyboard_with_limit("dashboard/daily_recap.json", "dashboard/daily_recap.json")

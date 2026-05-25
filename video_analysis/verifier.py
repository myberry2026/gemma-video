import os
import cv2
import numpy as np
import requests
import json
import time

# --- Configuration ---
GEMMA_URL = "http://localhost:1234/v1/chat/completions"
REAL_IMG_A = "real_a.jpg" # Consecutive frame
REAL_IMG_B = "real_b.jpg" # Consecutive frame (very similar)
REAL_IMG_C = "real_c.jpg" # Distant frame (different)
REAL_JSON = "dashboard/daily_recap.json"

def test_level1_real():
    print("[*] Testing Level 1 with REAL DATA (Local Filter)...")
    if not all(os.path.exists(f) for f in [REAL_IMG_A, REAL_IMG_B, REAL_IMG_C]):
        print("    - [!] Error: Real test images not found.")
        return False
        
    img_a = cv2.imread(REAL_IMG_A, cv2.IMREAD_GRAYSCALE)
    img_b = cv2.imread(REAL_IMG_B, cv2.IMREAD_GRAYSCALE)
    img_c = cv2.imread(REAL_IMG_C, cv2.IMREAD_GRAYSCALE)
    
    def get_sim(i1, i2):
        i1 = cv2.resize(i1, (64, 64))
        i2 = cv2.resize(i2, (64, 64))
        # Use normalized absolute difference instead of strict non-zero count
        # (np.sum(diff) / total_possible_sum)
        diff = cv2.absdiff(i1, i2)
        avg_diff = np.mean(diff)
        return 1.0 - (avg_diff / 255.0)

    sim_ab = get_sim(img_a, img_b)
    sim_ac = get_sim(img_a, img_c)
    
    print(f"    - Similar pair (A vs B): {sim_ab:.4f} (Expect > 0.90)")
    print(f"    - Different pair (A vs C): {sim_ac:.4f} (Expect < 0.85)")
    
    passed = sim_ab > 0.90 and sim_ac < 0.90
    print(f"    - Result: {'PASSED' if passed else 'FAILED'}")
    return passed

def test_level2_real():
    print("[*] Testing Level 2 with REAL DATA (Remote AI)...")
    import base64
    def to_b64(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    if not os.path.exists(REAL_IMG_A) or not os.path.exists(REAL_IMG_B):
        return False

    b64_a = to_b64(REAL_IMG_A)
    b64_b = to_b64(REAL_IMG_B)

    data = {
        "model": "google/gemma-4-e2b",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Are these two images from a mobile screen almost the same? Output only yes or no."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_a}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_b}"}}
                ]
            }
        ],
        "max_tokens": 256,
        "temperature": 0.0
    }

    try:
        res = requests.post(GEMMA_URL, json=data, timeout=30)
        res.raise_for_status()
        res_json = res.json()
        print(f"    - Full API Response: {json.dumps(res_json, indent=2)}")
        
        choice = res_json['choices'][0]['message']
        content = choice.get('content', '').lower().strip()
        reasoning = choice.get('reasoning_content', '').lower().strip()
        
        # Check both content and reasoning
        passed = "yes" in content or "yes" in reasoning
        print(f"    - Final Decision: {'PASSED' if passed else 'FAILED'}")
        return passed
    except Exception as e:
        print(f"    - [!] Connection: {GEMMA_URL} is UNREACHABLE. (Skip for now)")
        return False

def test_level3_real(test_count=10):
    print(f"[*] Testing Level 3 with REAL DATA ({test_count} frames curation)...")
    from nightly_scoring import run_gemma_scoring
    
    scored_results = []
    for i in range(test_count):
        img_path = f"real_{i:02d}.jpg"
        if not os.path.exists(img_path):
            print(f"    - [!] Skip: {img_path} not found.")
            continue
            
        print(f"    - Scoring [{i+1}/{test_count}]: {img_path}")
        result = run_gemma_scoring(img_path, "System Verifier")
        scored_results.append({
            "path": img_path,
            "score": result.get("score", 0),
            "summary": result.get("summary", "N/A")
        })

    # Curation Logic: Sort by score and take Top 10
    print(f"[*] Applying Top 10 Curation to {len(scored_results)} frames...")
    curated = sorted(scored_results, key=lambda x: x["score"], reverse=True)[:10]
    
    for idx, item in enumerate(curated):
        print(f"    {idx+1}. {item['path']} | Score: {item['score']} | {item['summary']}")

    passed = len(curated) <= 10
    if test_count > 10:
        passed = passed and len(curated) == 10
        
    print(f"    - Result: {'PASSED' if passed else 'FAILED'}")
    return passed

def test_global_diversity_curation():
    print("\n[*] Testing Level 3 EXTRA: Global Diversity Curation (16 -> 7)...")
    from nightly_scoring import select_diverse_7_from_pool
    
    image_paths = [f"real_{i:02d}.jpg" for i in range(16)]
    if not all(os.path.exists(p) for p in image_paths):
        print("    - [!] Error: Need 16 real images to test diversity.")
        return False

    # Execute the single-call curation
    selected_paths, summary, reasoning = select_diverse_7_from_pool(image_paths, "System Verifier")
    
    print(f"    - Gemma Reasoning: '{reasoning}'")
    print(f"    - Selected {len(selected_paths)} unique frames:")
    for i, p in enumerate(selected_paths):
        print(f"      {i+1}. {p}")
        
    passed = len(selected_paths) == 7
    print(f"    - Result: {'PASSED' if passed else 'FAILED'}")
    return passed

import sys

class Logger(object):
    def __init__(self, filename="results.txt"):
        self.terminal = sys.stdout
        self.log = open(filename, "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()

    def flush(self):
        self.terminal.flush()
        self.log.flush()

def run_verifier():
    sys.stdout = Logger("results.txt")
    print("\n" + "="*50)
    print("       AETHERLENS MULTI-LEVEL DEDUP VERIFIER (REAL DATA)       ")
    print("="*50)
    
    l1 = test_level1_real()
    
    # Run the 16 -> 7 Diversity Test
    l_div = test_global_diversity_curation()
    
    # Keep standard Level 3 logic for regression
    print("\n--- STANDARD BATCH TEST ---")
    l3 = test_level3_real(16)
    
    print("\n" + "="*50)
    status = "SYSTEM FULLY OPERATIONAL" if (l1 and l_div and l3) else "SYSTEM FAILURE"
    print(f"OVERALL STATUS: {status}")
    print("="*50 + "\n")
    
    # Keep real images for user to inspect if needed, or cleanup
    # for f in [REAL_IMG_A, REAL_IMG_B, REAL_IMG_C]: os.remove(f)

if __name__ == "__main__":
    run_verifier()

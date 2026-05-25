import requests
import json
import base64
import time
import sys
import os

# Configuration
BASE_URL = "http://localhost:8888" # Forwarded from device 8080
MODEL_PATH = "/data/data/com.gemma.videomemory/files/models/gemma-4-E2B-it.litertlm"

def test_health():
    print("[*] Testing /health...")
    res = requests.get(f"{BASE_URL}/health")
    print(f"    Status: {res.status_code}")
    print(f"    Body: {res.text}")
    return res.status_code == 200

def load_model(backend):
    print(f"[*] Loading model on {backend}...")
    data = {
        "path": MODEL_PATH,
        "backend": backend
    }
    try:
        res = requests.post(f"{BASE_URL}/models/load", json=data, timeout=60)
        print(f"    Status: {res.status_code}")
        print(f"    Body: {res.text}")
        return res.status_code == 200 and "success" in res.json()
    except Exception as e:
        print(f"    Error: {e}")
        return False

def test_text_inference():
    print("[*] Testing Text Inference...")
    data = {
        "model": "gemma-4-E2B-it",
        "messages": [
            {"role": "user", "content": "What is 2+2? Answer only with the number."}
        ],
        "temperature": 0.0
    }
    res = requests.post(f"{BASE_URL}/v1/chat/completions", json=data, timeout=60)
    if res.status_code == 200:
        content = res.json()["choices"][0]["message"]["content"].strip()
        print(f"    Response: {content}")
        return "4" in content
    else:
        print(f"    Failed: {res.status_code} - {res.text}")
        return False

def test_image_inference(image_path):
    print(f"[*] Testing Image Inference with {image_path}...")
    if not os.path.exists(image_path):
        print(f"    Error: {image_path} not found.")
        return False
        
    with open(image_path, "rb") as f:
        b64_img = base64.b64encode(f.read()).decode('utf-8')
        
    data = {
        "model": "gemma-4-E2B-it",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe the main color in this image."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]
            }
        ],
        "temperature": 0.0
    }
    
    start_time = time.time()
    res = requests.post(f"{BASE_URL}/v1/chat/completions", json=data, timeout=120)
    duration = time.time() - start_time
    
    if res.status_code == 200:
        content = res.json()["choices"][0]["message"]["content"]
        print(f"    Response: {content}")
        print(f"    Duration: {duration:.2f}s")
        return len(content) > 0
    else:
        print(f"    Failed: {res.status_code} - {res.text}")
        return False

def run_suite():
    print("="*50)
    print("       AETHERLENS LOCAL MODEL UNIT TESTS       ")
    print("="*50)
    
    results = {}
    
    # 1. Connectivity
    results["Health"] = test_health()
    if not results["Health"]:
        print("[!] Health check failed. Is the server running and port forwarded?")
        return

    # 2. Test CPU (Baseline)
    print("\n--- Testing CPU Backend ---")
    if load_model("cpu"):
        results["CPU_Text"] = test_text_inference()
        results["CPU_Image"] = test_image_inference("real_00.jpg")
    else:
        results["CPU_Load"] = False

    # 3. Test NPU
    print("\n--- Testing NPU Backend ---")
    if load_model("npu"):
        results["NPU_Text"] = test_text_inference()
        results["NPU_Image"] = test_image_inference("real_00.jpg")
    else:
        results["NPU_Load"] = False

    # 4. Test GPU
    print("\n--- Testing GPU Backend ---")
    if load_model("gpu"):
        results["GPU_Text"] = test_text_inference()
        results["GPU_Image"] = test_image_inference("real_00.jpg")
    else:
        results["GPU_Load"] = False

    print("\n" + "="*50)
    print("SUMMARY:")
    for test, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test:20}: {status}")
    print("="*50)

if __name__ == "__main__":
    run_suite()

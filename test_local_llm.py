import base64
import requests
import json
import sys

def test_multimodal(image_path):
    with open(image_path, "rb") as f:
        b64_img = base64.b64encode(f.read()).decode('utf-8')
        
    url = "http://localhost:8888/v1/chat/completions"
    data = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What app is this in the screenshot?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]
            }
        ],
        "temperature": 0.1
    }
    
    print(f"[*] Sending multimodal request for {image_path}...")
    res = requests.post(url, json=data, timeout=120)
    print(f"[+] Status: {res.status_code}")
    print(json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_multimodal(sys.argv[1])
    else:
        test_multimodal("real_00.jpg")

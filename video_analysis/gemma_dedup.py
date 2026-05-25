import torch
from transformers import AutoModelForMultimodalLM, AutoProcessor
from PIL import Image
import os
import requests
import json

# Gemma-4 Multimodal Semantic Deduplication Utility
# Asks the model if two images are "almost the same"

GEMMA_URL = "http://100.113.214.52:1234/v1/chat/completions"

def gemma4_is_duplicate(image_path1, image_path2, use_api=False):
    """
    Uses Gemma-4 to perform semantic deduplication between two images.
    Returns True if the model says 'yes' (they are the same).
    """
    if not os.path.exists(image_path1) or not os.path.exists(image_path2):
        return False

    prompt = "Are these two images almost the same? Output only yes or no."

    if use_api:
        # Assuming the local API supports multi-image chat completion
        # This is a mock structure; real API details might vary
        try:
            print(f"[*] Calling Gemma-4 API for semantic dedup...")
            # Note: Many local inference servers (like llama.cpp/vLLM) 
            # might require specific image encoding for multi-image
            data = {
                "model": "google/gemma-4-e2b",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"file://{os.path.abspath(image_path1)}"}},
                            {"type": "image_url", "image_url": {"url": f"file://{os.path.abspath(image_path2)}"}}
                        ]
                    }
                ],
                "max_tokens": 256,
                "temperature": 0.0
            }
            res = requests.post(GEMMA_URL, json=data, timeout=30)
            res.raise_for_status()
            res_json = res.json()
            choice = res_json['choices'][0]['message']
            content = choice.get('content', '').lower().strip()
            reasoning = choice.get('reasoning_content', '').lower().strip()
            
            return "yes" in content or "yes" in reasoning
        except Exception as e:
            print(f"[!] Gemma API dedup failed: {e}")
            return False
    else:
        # Local model loading (heavy, but more direct for the task)
        try:
            model_id = "google/gemma-4-E2B-it"
            processor = AutoProcessor.from_pretrained(model_id)
            model = AutoModelForMultimodalLM.from_pretrained(
                model_id,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                attn_implementation="sdpa"
            )

            img1 = Image.open(image_path1).convert("RGB")
            img2 = Image.open(image_path2).convert("RGB")

            content = [
                {"type": "image"},
                {"type": "image"},
                {"type": "text", "text": prompt}
            ]
            
            messages = [{"role": "user", "content": content}]
            
            # Apply chat template
            inputs = processor(
                images=[img1, img2],
                text=processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False),
                return_tensors="pt"
            ).to(model.device)

            with torch.no_grad():
                output = model.generate(**inputs, max_new_tokens=10)
            
            response = processor.decode(output[0], skip_special_tokens=True).lower()
            print(f"[+] Gemma-4 Dedup Response: {response}")
            return "yes" in response
        except Exception as e:
            print(f"[!] Local Gemma dedup failed: {e}")
            return False

if __name__ == "__main__":
    # Test with two existing images if available
    img_a = "test_a.jpg"
    img_b = "test_b.jpg"
    
    if os.path.exists(img_a) and os.path.exists(img_b):
        # We'll run the local check
        print(f"[*] Starting Semantic Dedup Test: {img_a} vs {img_b}")
        result = gemma4_is_duplicate(img_a, img_b, use_api=False)
        print(f"[*] Semantic Duplicate Check Result: {result}")
    else:
        print(f"[!] Test images not found at {img_a} or {img_b}")

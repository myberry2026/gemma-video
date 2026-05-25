import torch
from transformers import AutoModelForMultimodalLM, AutoProcessor
from decord import VideoReader, cpu
import numpy as np
from PIL import Image
import time
import os

# Ensure we use the correct environment
os.environ["PYTHONNOUSERSITE"] = "1"

def extract_one_frame(video_path):
    print(f"Extracting middle frame from {video_path}...")
    vr = VideoReader(video_path, ctx=cpu(0))
    # Get the middle frame for high-precision analysis
    frame_idx = len(vr) // 2
    frame = vr[frame_idx].asnumpy()
    return Image.fromarray(frame)

def run_image_inference(video_path, prompt):
    model_id = "google/gemma-4-E2B-it"
    
    print(f"Loading model for {model_id} (Official Image Cookbook Pattern)...")
    start_load = time.time()
    
    # Standard cookbook loading
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForMultimodalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa"
    )
    
    load_time = time.time() - start_load
    print(f"Model loaded in {load_time:.2f}s")

    # Extract one high-quality image
    image = extract_one_frame(video_path)

    # Official cookbook message structure for image
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    
    print("Preparing inputs (Official Image Template)...")
    start_prep = time.time()
    
    # Following the cookbook: apply_chat_template handles the <|image|> expansion
    inputs = processor.apply_chat_template(
        messages, 
        add_generation_prompt=True, 
        tokenize=True, 
        return_tensors="pt",
        return_dict=True
    )
    
    # Move to device
    inputs = {k: v.to(model.device) for k, v in inputs.items() if isinstance(v, torch.Tensor)}
    prep_time = time.time() - start_prep

    print("Generating response (High Precision)...")
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        
    start_gen = time.time()
    with torch.no_grad():
        output = model.generate(
            **inputs, 
            max_new_tokens=256,
            do_sample=True,
            temperature=0.7
        )
    gen_time = time.time() - start_gen
    
    print("Decoding result...")
    generated_ids = output[0][inputs["input_ids"].shape[-1]:]
    response = processor.decode(generated_ids, skip_special_tokens=True)
    
    return response, load_time, prep_time, gen_time, len(generated_ids)

if __name__ == "__main__":
    # Using the real-world bottle video for clear object analysis
    video_file = "real_world_traffic.mp4" 
    user_prompt = "Perform a high-precision analysis of this scene. Describe the objects, textures, and lighting in detail."
    
    try:
        result, l_t, p_t, g_t, tokens = run_image_inference(video_file, user_prompt)
        print("\n--- Response (Official Image Mode) ---")
        print(result.strip())
        print(f"\nStats: Load {l_t:.1f}s, Prep {p_t:.1f}s, Gen {g_t:.1f}s ({tokens/g_t:.2f} t/s)")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

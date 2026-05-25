import torch
from transformers import AutoModelForMultimodalLM, AutoProcessor
from decord import VideoReader, cpu
import numpy as np
from PIL import Image
import time
import os

# Ensure we use the correct environment
os.environ["PYTHONNOUSERSITE"] = "1"

def extract_frames(video_path, num_frames=16):
    print(f"Manually extracting {num_frames} frames from {video_path}...")
    vr = VideoReader(video_path, ctx=cpu(0))
    total_frames = len(vr)
    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames = vr.get_batch(indices).asnumpy()
    
    # Convert numpy frames to PIL Images
    pil_images = [Image.fromarray(frame) for frame in frames]
    return pil_images

def run_multi_image_inference(video_path, prompt):
    model_id = "google/gemma-4-E2B-it"
    
    print(f"Loading model for {model_id} (Multi-Image Mode BF16)...")
    start_load = time.time()
    
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForMultimodalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa"
    )
    
    load_time = time.time() - start_load
    print(f"Model loaded in {load_time:.2f}s")

    # Manually extract images
    images = extract_frames(video_path, num_frames=16)

    # Build multi-image message structure
    # For Gemma 4, each image expands into a specific number of tokens
    num_image_tokens = processor.video_processor.max_soft_tokens # Usually 70
    image_prompt = "<|image|>" * num_image_tokens
    
    content = []
    for _ in range(len(images)):
        # Important: The chat template needs to know where the images are
        content.append({"type": "image"})
    content.append({"type": "text", "text": f"These are 16 sequential frames from a video. {prompt}"})

    messages = [
        {
            "role": "user",
            "content": content,
        }
    ]
    
    print("Preparing inputs (Processor handling 16 individual images)...")
    start_prep = time.time()
    
    # Use the processor directly for multi-modal input
    inputs = processor(
        text=f"These are 16 sequential frames from a video. {prompt}",
        images=images,
        return_tensors="pt"
    )
    
    # Apply chat template for correct formatting
    messages = [
        {
            "role": "user",
            "content": content,
        }
    ]
    chat_inputs = processor.apply_chat_template(
        messages, 
        add_generation_prompt=True, 
        tokenize=True, 
        return_tensors="pt",
        return_dict=True
    )
    
    # Merge the tokens from chat template with pixel values from processor
    inputs.update({"input_ids": chat_inputs["input_ids"], "attention_mask": chat_inputs["attention_mask"]})

    # Move to device
    inputs = {k: v.to(model.device) for k, v in inputs.items() if isinstance(v, torch.Tensor)}
    prep_time = time.time() - start_prep

    print("Generating response...")
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        
    start_gen = time.time()
    with torch.no_grad():
        output = model.generate(
            **inputs, 
            max_new_tokens=256,
            do_sample=True,
            temperature=0.7,
            top_p=0.9
        )
    gen_time = time.time() - start_gen
    
    print("Decoding result...")
    generated_ids = output[0][inputs["input_ids"].shape[-1]:]
    response = processor.decode(generated_ids, skip_special_tokens=True)
    
    return response, load_time, prep_time, gen_time, len(generated_ids)

if __name__ == "__main__":
    video_file = "real_world_traffic.mp4" # Using the bottle conveyor belt one
    user_prompt = "Count the objects and describe their movement across these 16 frames."
    
    try:
        result, l_t, p_t, g_t, tokens = run_multi_image_inference(video_file, user_prompt)
        print("\n--- Response (Multi-Image Mode) ---")
        print(result.strip())
        print(f"\nStats: Load {l_t:.1f}s, Prep {p_t:.1f}s, Gen {g_t:.1f}s ({tokens/g_t:.2f} t/s)")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

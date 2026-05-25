import torch
from transformers import AutoModelForMultimodalLM, AutoProcessor
import time
import os

# Ensure we use the correct environment
os.environ["PYTHONNOUSERSITE"] = "1"

def run_inference(video_path, prompt):
    model_id = "google/gemma-4-E2B-it"
    
    print(f"Loading model and processor for {model_id} (Token-Optimized BF16)...")
    start_load = time.time()
    
    # 16-frame optimization (Sweet Spot)
    processor = AutoProcessor.from_pretrained(model_id)
    processor.video_processor.num_frames = 16 
    
    model = AutoModelForMultimodalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa"
    )
    
    load_time = time.time() - start_load
    print(f"Model loaded in {load_time:.2f}s")

    # Original cookbook template structure:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "video", "video": video_path},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    
    print("Preparing inputs (processor handling video extraction)...")
    start_prep = time.time()
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
            top_p=0.9,
            repetition_penalty=1.1
        )
    gen_time = time.time() - start_gen
    
    print("Decoding result...")
    generated_ids = output[0][inputs["input_ids"].shape[-1]:]
    response = processor.decode(generated_ids, skip_special_tokens=True)
    
    return response, load_time, prep_time, gen_time, len(generated_ids)

if __name__ == "__main__":
    # Complex real-world traffic video
    video_file = "real_world_traffic.mp4"
    user_prompt = "Provide a detailed analysis of the traffic flow, identifying different types of vehicles and any pedestrian activity."
    
    try:
        result, l_t, p_t, g_t, tokens = run_inference(video_file, user_prompt)
        print("\n--- Response ---")
        print(result.strip())
        print(f"\nStats: Load {l_t:.1f}s, Prep {p_t:.1f}s, Gen {g_t:.1f}s ({tokens/g_t:.2f} t/s)")
    except Exception as e:
        print(f"\nError: {e}")

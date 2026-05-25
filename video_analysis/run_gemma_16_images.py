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
    return [Image.fromarray(frame) for frame in frames]

def run_16_image_inference(video_path, prompt):
    model_id = "google/gemma-4-E2B-it"
    
    print(f"Loading model for {model_id} (16-Image High Precision BF16)...")
    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForMultimodalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa"
    )
    
    images = extract_frames(video_path, num_frames=16)

    # We will manually construct the multi-image prompt to ensure token alignment
    # Based on previous error, each image needs 264 tokens
    # Total features: 16 * 264 = 4224
    
    # We'll use the apply_chat_template but we'll check its output
    content = [{"type": "image"} for _ in range(16)]
    content.append({"type": "text", "text": prompt})
    
    messages = [{"role": "user", "content": content}]
    
    print("Preparing inputs and checking token expansion...")
    # Get the raw tokens from template
    inputs = processor.apply_chat_template(
        messages, 
        add_generation_prompt=True, 
        tokenize=True, 
        return_tensors="pt",
        return_dict=True
    )
    
    # Process images separately to get all required tensors (pixel_values, position_ids, etc.)
    image_inputs = processor(text=prompt, images=images, return_tensors="pt")
    
    # We want to use the chat template for input_ids to get the correct turn formatting
    messages = [{"role": "user", "content": content}]
    chat_inputs = processor.apply_chat_template(
        messages, 
        add_generation_prompt=True, 
        tokenize=True, 
        return_tensors="pt",
        return_dict=True
    )
    
    # Merge them: Take everything from image_inputs and override input_ids/attention_mask from chat
    inputs = {k: v for k, v in image_inputs.items()}
    inputs.update({
        "input_ids": chat_inputs["input_ids"],
        "attention_mask": chat_inputs["attention_mask"]
    })
    
    # Move ALL tensors to device
    inputs = {k: v.to(model.device) for k, v in inputs.items() if isinstance(v, torch.Tensor)}
    
    print(f"Input IDs shape: {inputs['input_ids'].shape}")
    print(f"Pixel values shape: {inputs['pixel_values'].shape}")
    
    # HACK: If input_ids only has 16 image placeholders, we might need to manually expand them
    # But let's see if the generate() call handles it now that we have pixel_values
    
    print("Generating response (This will be SLOW due to 4000+ visual tokens)...")
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        
    start_gen = time.time()
    with torch.no_grad():
        try:
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
            return response, gen_time, len(generated_ids)
        except ValueError as ve:
            print(f"\nCaught Token Mismatch: {ve}")
            print("Attempting Manual Token Expansion Hack...")
            
            # Manual Fix: Replace each single <|image|> token with 264 placeholder tokens
            # We need to find the token id for <|image|>
            image_token_id = processor.tokenizer.convert_tokens_to_ids("<|image|>")
            
            new_input_ids = []
            for token_id in inputs["input_ids"][0]:
                if token_id == image_token_id:
                    # Expand 1 token into 264 tokens
                    new_input_ids.extend([image_token_id] * 264)
                else:
                    new_input_ids.append(token_id)
            
            inputs["input_ids"] = torch.tensor([new_input_ids]).to(model.device)
            # Rebuild attention mask
            inputs["attention_mask"] = torch.ones_like(inputs["input_ids"]).to(model.device)
            
            print(f"RETRY: New Input IDs shape: {inputs['input_ids'].shape}")
            
            start_gen = time.time()
            output = model.generate(**inputs, max_new_tokens=256, do_sample=True, temperature=0.7)
            gen_time = time.time() - start_gen
            
            generated_ids = output[0][inputs["input_ids"].shape[-1]:]
            response = processor.decode(generated_ids, skip_special_tokens=True)
            return response, gen_time, len(generated_ids)

if __name__ == "__main__":
    video_file = "real_world_traffic.mp4"
    user_prompt = "Analyze these 16 images in high precision. Describe the movement of the bottles and any details of the machinery."
    
    try:
        result, g_t, tokens = run_16_image_inference(video_file, user_prompt)
        print("\n--- Response (16-Image High Precision) ---")
        print(result.strip())
        print(f"\nStats: Gen {g_t:.1f}s ({tokens/g_t:.2f} t/s)")
    except Exception as e:
        print(f"\nCritical Error: {e}")
        import traceback
        traceback.print_exc()

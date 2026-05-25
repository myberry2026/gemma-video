import torch
from transformers import AutoModelForMultimodalLM, AutoProcessor
from decord import VideoReader, cpu
import numpy as np
from PIL import Image
import time
import os

# Ensure we use the correct environment
os.environ["PYTHONNOUSERSITE"] = "1"

def extract_frames(video_path, num_frames=8):
    print(f"Manually extracting {num_frames} frames from {video_path}...")
    vr = VideoReader(video_path, ctx=cpu(0))
    total_frames = len(vr)
    indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
    frames = vr.get_batch(indices).asnumpy()
    return [Image.fromarray(frame) for frame in frames]

def run_lowres_8img_inference(video_path, prompt):
    model_id = "google/gemma-4-E2B-it"
    
    print(f"Loading model for {model_id} (8-Image Low-Res Precision BF16)...")
    processor = AutoProcessor.from_pretrained(model_id)
    
    # Set to lowest possible resolution (same as video mode)
    processor.video_processor.max_soft_tokens = 70
    
    model = AutoModelForMultimodalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa"
    )
    
    images = extract_frames(video_path, num_frames=8)

    content = [{"type": "image"} for _ in range(8)]
    content.append({"type": "text", "text": prompt})
    messages = [{"role": "user", "content": content}]
    
    print(f"Preparing inputs (Target: 8 images @ {processor.video_processor.max_soft_tokens} tokens each)...")
    
    # Process images with the lower token count
    image_inputs = processor(text=prompt, images=images, return_tensors="pt")
    
    chat_inputs = processor.apply_chat_template(
        messages, 
        add_generation_prompt=True, 
        tokenize=True, 
        return_tensors="pt",
        return_dict=True
    )
    
    inputs = {k: v for k, v in image_inputs.items()}
    inputs.update({
        "input_ids": chat_inputs["input_ids"],
        "attention_mask": chat_inputs["attention_mask"]
    })
    
    inputs = {k: v.to(model.device) for k, v in inputs.items() if isinstance(v, torch.Tensor)}
    
    print("Checking for token expansion need...")
    # Get total visual features from pixel_values or similar
    # The actual features produced for 70 tokens is often higher due to pooling
    # Let's dynamically detect from the error if it fails, or use pixel_values shape
    expected_features = inputs["pixel_values_videos"].shape[1] * inputs["pixel_values_videos"].shape[2] if "pixel_values_videos" in inputs else inputs["pixel_values"].shape[1]
    
    # For Gemma 4, image field with 70 tokens actually produces 630 features (70 * 3^2)
    # We will manually expand to match expected_features
    image_token_id = processor.tokenizer.convert_tokens_to_ids("<|image|>")
    
    new_input_ids = []
    for token_id in inputs["input_ids"][0]:
        if token_id == image_token_id:
            # Distribute expected_features among the 8 images
            new_input_ids.extend([image_token_id] * (expected_features // 8))
        else:
            new_input_ids.append(token_id)
            
    inputs["input_ids"] = torch.tensor([new_input_ids]).to(model.device)
    inputs["attention_mask"] = torch.ones_like(inputs["input_ids"]).to(model.device)
    print(f"Final Input IDs shape: {inputs['input_ids'].shape}, Features: {expected_features}")

    print("Generating response...")
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
    
    generated_ids = output[0][inputs["input_ids"].shape[-1]:]
    response = processor.decode(generated_ids, skip_special_tokens=True)
    
    return response, gen_time, len(generated_ids), expected_features

if __name__ == "__main__":
    video_file = "real_world_traffic.mp4"
    user_prompt = "Identify the key action in these 8 frames and describe any machinery."
    
    try:
        result, g_t, tokens, total_v = run_lowres_8img_inference(video_file, user_prompt)
        print("\n--- Response (8-Image Low-Res Precision) ---")
        print(result.strip())
        print(f"\nStats:")
        print(f"- Visual Tokens: {total_v}")
        print(f"- Generation:    {g_t:.1f}s ({tokens/g_t:.2f} t/s)")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

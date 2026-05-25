import torch
from transformers import AutoModelForMultimodalLM, AutoProcessor
import os

os.environ["PYTHONNOUSERSITE"] = "1"

def check_model_perf():
    model_id = "google/gemma-4-E2B-it"
    print(f"--- Performance Check for {model_id} ---")
    
    model = AutoModelForMultimodalLM.from_pretrained(
        model_id,
        device_map="auto",
        torch_dtype=torch.bfloat16
    )
    
    # 1. 检查模型分布
    print("\n[1] Device Map (模型层分布):")
    device_map = getattr(model, "hf_device_map", None)
    if device_map:
        for name, device in device_map.items():
            if device != 0:
                print(f"!!! WARNING: Layer {name} is on device: {device}")
        if all(d == 0 for d in device_map.values()):
            print("Success: All layers are on GPU:0")
    else:
        # Fallback: check parameters
        devices = {p.device for p in model.parameters()}
        print(f"Model parameters are on: {devices}")

    # 3. 检查注意力机制
    config = model.config
    print(f"\n[3] Attention Implementation: {getattr(config, '_attn_implementation', 'default')}")

    # 2. 检查处理器默认采样
    processor = AutoProcessor.from_pretrained(model_id)
    video_proc = processor.video_processor
    print(f"\n[2] Video Sampling Config:")
    print(f"- num_frames (默认采样帧数): {video_proc.num_frames}")
    print(f"- max_soft_tokens (每帧Token): {video_proc.max_soft_tokens}")
    
    total_v_tokens = video_proc.num_frames * video_proc.max_soft_tokens
    print(f"- Total Visual Tokens: {total_v_tokens}")

if __name__ == "__main__":
    check_model_perf()

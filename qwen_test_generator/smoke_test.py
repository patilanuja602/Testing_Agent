"""Smoke test for Qwen3-8B 4-bit inference pipeline."""
import os
import sys
import time
import gc
from pathlib import Path

# Ensure local offline loading
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch

def run_smoke_test():
    print("=" * 60)
    print("QWEN3-8B 4-BIT PIPELINE SMOKE TEST")
    print("=" * 60)

    # 1. Locate ./models/Qwen3-8B
    model_path = Path("./models/Qwen3-8B")
    if not model_path.exists():
        candidate = PROJECT_ROOT / "models" / "Qwen3-8B"
        if candidate.exists():
            model_path = candidate
        else:
            raise FileNotFoundError(f"Model directory not found at '{model_path}' or '{candidate}'.")
    print(f"[1/8] Model located at: {model_path.resolve()}")

    # 2. Check CUDA & BitsAndBytes
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available! GPU execution is required.")
    print(f"[2/8] CUDA available: {torch.cuda.get_device_name(0)}")

    try:
        import bitsandbytes
        print(f"[3/8] BitsAndBytes available: v{bitsandbytes.__version__}")
    except ImportError as e:
        raise ImportError(f"BitsAndBytes is not installed or failed to import: {e}") from e

    # 3. Load Tokenizer & Model in 4-bit using project model_loader
    from model.model_loader import load_model
    print("[4/8] Loading model and tokenizer via load_model (4-bit)...")
    t0_load = time.time()
    model, tokenizer = load_model(str(model_path), quantization="4bit")
    load_time = time.time() - t0_load
    print(f"      Model and tokenizer successfully loaded in {load_time:.2f}s")

    # 4. Confirm CUDA is being used
    primary_device = str(getattr(model, "device", "unknown"))
    if "cuda" not in primary_device:
        device_map = getattr(model, "hf_device_map", {})
        if not any("cuda" in str(d) for d in device_map.values()):
            raise RuntimeError(f"Model is NOT running on CUDA! Device: {primary_device}, Map: {device_map}")
    print(f"[5/8] Confirmed CUDA execution device: {primary_device}")
    print(f"      GPU VRAM allocated: {torch.cuda.memory_allocated(0) / (1024**3):.2f} GB")

    # 5. Generate one very small test response
    prompt = "Give one simple software test case for a login page."
    print(f"[6/8] Generating small response for prompt: \"{prompt}\"")
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    prompt_len = inputs["input_ids"].shape[1]

    t0_gen = time.time()
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=40,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
        )
    gen_time = time.time() - t0_gen

    # 6 & 7. Print generation time and short portion of generated response
    new_tokens = out[0][prompt_len:]
    response_text = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
    print(f"[7/8] Generation completed in {gen_time:.2f}s ({len(new_tokens)} tokens, {len(new_tokens)/max(gen_time, 0.001):.2f} tokens/s)")
    print("=" * 60)
    print("GENERATED SAMPLE OUTPUT (Short Portion):")
    print("-" * 60)
    print(response_text[:300])
    print("=" * 60)

    # 8. Release model resources cleanly
    print("[8/8] Releasing model resources cleanly...")
    del model
    del tokenizer
    gc.collect()
    torch.cuda.empty_cache()
    print(f"      GPU VRAM after cleanup: {torch.cuda.memory_allocated(0) / (1024**3):.2f} GB allocated")
    print(">>> SMOKE TEST PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    run_smoke_test()


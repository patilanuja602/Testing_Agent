"""Script to download Qwen3-8B model safetensor weights from Hugging Face into the local directory."""
import sys
import subprocess
from pathlib import Path

MODEL_ID = "Qwen/Qwen3-8B"
DEST_DIR = Path(__file__).resolve().parent / "models" / "Qwen3-8B"

def main():
    print("=" * 60)
    print(f"Downloading {MODEL_ID} weights to {DEST_DIR}...")
    print("=" * 60)
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        sys.executable, "-m", "huggingface_hub.cli.hf",
        "download", MODEL_ID,
        "--local-dir", str(DEST_DIR)
    ]
    try:
        subprocess.run(cmd, check=True)
        print("\nModel weights downloaded successfully!")
    except Exception as e:
        print(f"\nStandard hf command failed: {e}")
        print("Trying huggingface_hub snapshot_download...")
        from huggingface_hub import snapshot_download
        snapshot_download(repo_id=MODEL_ID, local_dir=str(DEST_DIR), local_dir_use_symlinks=False)
        print("\nModel weights downloaded successfully via snapshot_download!")

if __name__ == "__main__":
    main()

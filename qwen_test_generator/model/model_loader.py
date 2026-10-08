"""Loads a Qwen3 model from a LOCAL directory only. Uses the GPU if present, otherwise falls back to CPU."""
import os
import time
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import psutil
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

PROJECT_DIR = Path(__file__).resolve().parent.parent
LOCAL_MODEL_DIR = PROJECT_DIR / "models" / "Qwen3-8B"
DEFAULT_MODEL_PATH = os.environ.get("QWEN_MODEL_PATH", str(LOCAL_MODEL_DIR) if LOCAL_MODEL_DIR.exists() else "./models/Qwen3-8B")


class ModelLoadError(Exception):
    """Base class for model loading problems."""


class ModelNotFoundError(ModelLoadError):
    pass


class InsufficientMemoryError(ModelLoadError):
    pass


def describe_device() -> str:
    if torch.cuda.is_available():
        names = [f"{torch.cuda.get_device_name(i)} ({torch.cuda.get_device_properties(i).total_memory / (1024**3):.1f}GB)"
                 for i in range(torch.cuda.device_count())]
        return "GPU (CUDA): " + ", ".join(names)
    return "CPU (no CUDA GPU detected - generation will be slow)"


def _model_size_gb(path: Path) -> float:
    return sum(f.stat().st_size for f in path.glob("*.safetensors")) / 1e9


def load_model(model_path: str = DEFAULT_MODEL_PATH, quantization: str = "4bit"):
    """Auto-selects device: CUDA GPU(s) if available, else CPU.
    quantization: '4bit' (recommended default), '8bit', or 'none'."""
    t0 = time.time()
    path = Path(model_path).expanduser()
    if not path.is_dir() or not (path / "config.json").exists():
        # Fallback to project root models path if called from a subfolder or root
        candidate = Path(__file__).resolve().parent.parent / model_path.lstrip("./")
        if candidate.is_dir() and (candidate / "config.json").exists():
            path = candidate
        else:
            raise ModelNotFoundError(
                f"Model not found at '{path}'. Put the model files in that folder or set QWEN_MODEL_PATH. See README."
            )

    use_gpu = torch.cuda.is_available()
    compute_dtype = torch.bfloat16
    kwargs = dict(local_files_only=True, dtype=compute_dtype)

    gpu_name = "N/A"
    gpu_vram = 0.0
    selected_device = "cpu"

    if use_gpu:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)

        if quantization == "4bit":
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=compute_dtype,
            )
            # 8B in 4-bit fits directly in GPU VRAM without CPU offload
            kwargs["device_map"] = {"": 0}
            selected_device = f"cuda:0 ({gpu_name})"
        elif quantization == "8bit":
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_8bit=True,
            )
            kwargs["device_map"] = "auto"
            selected_device = f"cuda:0 ({gpu_name})"
        elif quantization == "none":
            # 8B in unquantized BF16 (~16GB) on an 8GB GPU requires offloading
            kwargs["device_map"] = "auto"
            selected_device = f"cuda (split/offloaded)"
        else:
            raise ModelLoadError(f"Unsupported quantization '{quantization}'. Choose '4bit', '8bit', or 'none'.")
    else:
        if quantization != "none":
            raise ModelLoadError("4bit/8bit quantization requires a CUDA GPU. Set Precision to 'none' on CPU.")
        selected_device = "cpu"

    try:
        tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(str(path), **kwargs)
        if not use_gpu:
            model.to("cpu")
        model.eval()

        load_time = time.time() - t0
        print("=" * 60)
        print("MODEL LOADER REPORT")
        print(f"Model Path:         {path}")
        print(f"Quantization Mode:  {quantization}")
        print(f"GPU Name:           {gpu_name}")
        print(f"GPU VRAM:           {gpu_vram:.2f} GB")
        print(f"Selected Device:    {selected_device}")
        print(f"Compute Dtype:      {compute_dtype}")
        print(f"Loading Time:       {load_time:.2f}s")
        print("=" * 60)

        return model, tokenizer
    except InsufficientMemoryError:
        raise
    except torch.cuda.OutOfMemoryError as e:
        raise InsufficientMemoryError(
            "GPU ran out of memory while loading. Try 4-bit precision or free GPU memory."
        ) from e
    except (RuntimeError, MemoryError) as e:
        if "out of memory" in str(e).lower() or isinstance(e, MemoryError):
            raise InsufficientMemoryError(f"Out of memory while loading the model: {e}") from e
        raise ModelLoadError(f"Model loading failed: {e}") from e
    except Exception as e:  # noqa: BLE001
        raise ModelLoadError(f"Model loading failed: {type(e).__name__}: {e}") from e

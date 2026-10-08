"""Saves each experiment as outputs/experiment_NNN.json (never overwrites)."""
import hashlib
import json
import platform
import re
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"


def _next_number(out_dir: Path) -> int:
    nums = [int(m.group(1)) for p in out_dir.glob("experiment_*.json")
            if (m := re.match(r"experiment_(\d+)\.json", p.name))]
    return max(nums, default=0) + 1


def save_experiment(*, model_name, model_path, quantization, params: dict, scenario: str, result: dict,
                    prompt_file: Path, out_dir: Path = OUTPUT_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        import torch, transformers
        versions = {"torch": torch.__version__, "transformers": transformers.__version__,
                    "python": platform.python_version()}
    except Exception:  # noqa: BLE001
        versions = {}
    prompt_hash = hashlib.sha256(Path(prompt_file).read_bytes()).hexdigest()

    n = _next_number(out_dir)
    while True:
        exp_id = f"experiment_{n:03d}"
        path = out_dir / f"{exp_id}.json"
        record = {
            "experiment_id": exp_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": model_name,
            "model_path": str(model_path),
            "quantization": quantization,
            "temperature": params["temperature"],
            "top_p": params["top_p"],
            "top_k": params["top_k"],
            "max_new_tokens": params["max_new_tokens"],
            "seed": params["seed"],
            "enable_thinking": params["enable_thinking"],
            "timeout_seconds": params["timeout_seconds"],
            "input_scenario": scenario,
            "prompt": result["prompt"],
            "prompt_file_sha256": prompt_hash,
            "rendered_prompt": result["rendered_prompt"],
            "raw_output": result["raw_output"],
            "status": result["status"],
            "error": result["error"],
            "parse_error": result["parse_error"],
            "generated_tokens": result["generated_tokens"],
            "truncated_at_max_tokens": result["truncated_at_max_tokens"],
            "duration_seconds": result["duration_seconds"],
            "parsed_output": result["parsed"],
            "parsed_test_cases": result["parsed_test_cases"],
            "environment": versions,
        }
        try:
            with open(path, "x", encoding="utf-8") as f:   # 'x' = fail if exists
                json.dump(record, f, indent=2, ensure_ascii=False)
            return path
        except FileExistsError:
            n += 1

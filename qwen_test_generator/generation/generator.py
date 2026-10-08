"""Sends the scenario to the local model and returns raw output + best-effort parsing.

The raw output is ALWAYS returned, whatever happens afterwards.
"""
import json
import re
import time
from dataclasses import dataclass, asdict

import torch

from generation.prompt_template import build_prompt


@dataclass
class GenerationParams:
    temperature: float = 0.7
    top_p: float = 0.8
    top_k: int = 20
    max_new_tokens: int = 6000
    seed: int = 42
    enable_thinking: bool = False      # Qwen3 thinking mode; recorded with every experiment
    timeout_seconds: int = 900

    def to_dict(self):
        return asdict(self)


def parse_output(raw: str):
    """Returns (parsed_dict_or_None, error_message_or_None). Never raises."""
    if not raw or not raw.strip():
        return None, "Model returned empty output."
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None, "Malformed output: no JSON object found."
    try:
        obj = json.loads(text[start:end + 1])
    except json.JSONDecodeError as e:
        return None, f"JSON parsing failed: {e}"
    if not isinstance(obj, dict):
        return None, "Malformed output: top-level JSON is not an object."
    if not isinstance(obj.get("test_cases"), list):
        return obj, "Parsed JSON has no 'test_cases' list."
    return obj, None


def generate_test_cases(model, tokenizer, scenario: str, params: GenerationParams) -> dict:
    prompt = build_prompt(scenario)
    rendered = tokenizer.apply_chat_template(
        [{"role": "user", "content": prompt}],
        tokenize=False, add_generation_prompt=True, enable_thinking=params.enable_thinking,
    )
    result = {
        "status": "ok", "error": None, "prompt": prompt, "rendered_prompt": rendered,
        "raw_output": "", "parsed": None, "parse_error": None, "parsed_test_cases": [],
        "generated_tokens": 0, "truncated_at_max_tokens": False, "duration_seconds": 0.0,
    }
    t0 = time.time()
    try:
        torch.manual_seed(params.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(params.seed)
        inputs = tokenizer(rendered, return_tensors="pt").to(model.device)
        gen_kwargs = dict(max_new_tokens=params.max_new_tokens, max_time=params.timeout_seconds,
                          pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id)
        if params.temperature and params.temperature > 0:
            gen_kwargs.update(do_sample=True, temperature=params.temperature,
                              top_p=params.top_p, top_k=params.top_k)
        else:
            gen_kwargs.update(do_sample=False)
        with torch.no_grad():
            out = model.generate(**inputs, **gen_kwargs)
        new_tokens = out[0][inputs["input_ids"].shape[1]:]
        result["generated_tokens"] = int(new_tokens.shape[0])
        result["raw_output"] = tokenizer.decode(new_tokens, skip_special_tokens=True)
        result["truncated_at_max_tokens"] = result["generated_tokens"] >= params.max_new_tokens
        elapsed = time.time() - t0
        if elapsed >= params.timeout_seconds and not result["truncated_at_max_tokens"]:
            result["status"] = "timeout"
            result["error"] = f"Generation stopped at the {params.timeout_seconds}s timeout; output is partial."
    except torch.cuda.OutOfMemoryError:
        result["status"] = "error"
        result["error"] = ("CUDA out of memory during generation. Reduce max_new_tokens or free GPU memory.")
    except Exception as e:  # noqa: BLE001
        result["status"] = "error"
        result["error"] = f"Generation failed: {type(e).__name__}: {e}"
    result["duration_seconds"] = round(time.time() - t0, 2)

    parsed, perr = parse_output(result["raw_output"])
    result["parsed"], result["parse_error"] = parsed, perr
    if result["truncated_at_max_tokens"] and perr:
        result["parse_error"] = f"{perr} (output hit max_new_tokens - likely truncated; raise the limit)"
    if isinstance(parsed, dict) and isinstance(parsed.get("test_cases"), list):
        result["parsed_test_cases"] = parsed["test_cases"]
    return result

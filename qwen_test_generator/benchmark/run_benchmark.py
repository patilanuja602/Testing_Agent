"""Benchmark runner for Qwen3-8B 4-bit baseline capability study across 34 project scenarios."""
import os
import sys
import time
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Set offline flags
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

# Add project root to sys.path
BENCHMARK_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BENCHMARK_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import torch
from model.model_loader import DEFAULT_MODEL_PATH, load_model


def build_prompt_for_case(case: dict) -> str:
    """Builds standardized capability prompt enforcing Section 10 fixed output structures."""
    cap = case["capability"]
    inp = case["input"]

    if cap in ("Unit Test Generation", "Integration Test Generation"):
        return (
            f"You are a senior software verification engineer for critical embedded and control systems.\n"
            f"Analyze the following requirement and system specification, then derive rigorous test cases.\n\n"
            f"{inp}\n\n"
            f"## INSTRUCTIONS & CONSTRAINTS:\n"
            f"1. Derive concrete, executable test cases directly from the requirements.\n"
            f"2. Clearly distinguish between EXPLICIT REQUIREMENTS and ASSUMPTIONS / DOMAIN EXPECTATIONS.\n"
            f"   Do NOT invent unstated numerical limits, timeouts, or business policies.\n"
            f"3. For every test case, use EXACTLY this structure:\n\n"
            f"TEST CASE ID: [e.g. TC-001]\n"
            f"REQUIREMENT REFERENCE: [Requirement clause or ID]\n"
            f"TEST TYPE: [Functional | Negative | Boundary | Security | State Transition | Recovery | etc.]\n"
            f"OBJECTIVE: [Concise statement of what is being verified]\n"
            f"PRECONDITIONS: [Initial system state or hardware setup]\n"
            f"INPUT / STIMULUS: [Concrete inputs, parameters, or signals]\n"
            f"STEPS: [Numbered step-by-step procedure]\n"
            f"EXPECTED RESULT: [Deterministic, verifiable expected outcome]\n"
            f"SOURCE / BASIS: [Must be exactly one of: Explicit Requirement | Logical Invariant | Domain Expectation | Assumption]\n"
            f"ASSUMPTIONS: [Explicitly state any unverified assumption, or 'None']\n"
        )
    elif cap == "MISRA / Static Analysis":
        return (
            f"You are a senior embedded software engineer and static-analysis triage specialist.\n"
            f"Analyze the following static analysis / MISRA finding report.\n\n"
            f"{inp}\n\n"
            f"## INSTRUCTIONS & CONSTRAINTS:\n"
            f"1. Explain what the finding means and the exact code construct causing it.\n"
            f"2. Evaluate potential risks and remediation options.\n"
            f"3. Distinguish between FACT FROM PROVIDED INPUT, MODEL REASONING, and ASSUMPTIONS.\n"
            f"4. Do NOT blindly declare a finding to be a false positive without proof.\n"
            f"5. If the supplied code or context is missing or insufficient to make a determination, "
            f"explicitly state: 'Insufficient information to determine.' Do NOT fabricate rules, project deviation approvals, or company coding standards.\n"
            f"6. Use EXACTLY this structure:\n\n"
            f"FINDING: [Summary of the diagnostic report]\n"
            f"RULE: [Rule ID and rule requirement statement]\n"
            f"CODE CONTEXT: [The specific line and construct triggering the violation]\n"
            f"ANALYSIS: [Technical explanation of the violation and mechanism]\n"
            f"RISK: [Potential safety, reliability, or undefined behavior risk]\n"
            f"RECOMMENDED ACTION: [Specific compliant code refactoring or action]\n"
            f"TEST IMPACT: [Specific unit/regression tests needed to verify remediation]\n"
            f"CONFIDENCE: [High | Medium | Low | Insufficient Information to Determine]\n"
            f"ASSUMPTIONS: [Explicitly state any assumptions made, or 'None']\n"
        )
    elif cap == "Regression Suite Upkeep":
        return (
            f"You are a senior software test architect managing automated regression test suites.\n"
            f"Analyze the following requirement modification and determine the exact regression test impact.\n\n"
            f"{inp}\n\n"
            f"## INSTRUCTIONS & CONSTRAINTS:\n"
            f"1. Reason about IMPACT rather than blindly regenerating every test.\n"
            f"2. Clearly identify:\n"
            f"   - Which existing tests remain valid without modification.\n"
            f"   - Which existing tests require modification (and what needs to change).\n"
            f"   - Which new tests must be added to cover the change.\n"
            f"   - Which existing tests are now obsolete and should be retired.\n"
            f"   - Why each test is affected.\n"
            f"3. For all modified or newly added test cases, use EXACTLY this structure:\n\n"
            f"TEST CASE ID: [e.g. TC_MOD_01 or TC_NEW_01]\n"
            f"REQUIREMENT REFERENCE: [Requirement ID and revision]\n"
            f"TEST TYPE: [Unit | Integration | Regression]\n"
            f"OBJECTIVE: [What is being verified and why it addresses the change]\n"
            f"PRECONDITIONS: [Initial state]\n"
            f"INPUT / STIMULUS: [Inputs and stimulus]\n"
            f"STEPS: [Execution steps]\n"
            f"EXPECTED RESULT: [Verifiable outcome]\n"
            f"SOURCE / BASIS: [Must be exactly one of: Explicit Requirement | Logical Invariant | Domain Expectation | Assumption]\n"
            f"ASSUMPTIONS: [Explicitly state any unverified assumption, or 'None']\n"
        )
    else:
        return inp


def run_benchmark(mode_arg="both", cases_filter=None, run_dir_arg=None):
    cases_file = BENCHMARK_DIR / "project_test_cases.json"
    if not cases_file.exists():
        raise FileNotFoundError(f"Benchmark test cases not found at {cases_file}")

    with open(cases_file, "r") as f:
        bench_data = json.load(f)
    all_cases = bench_data["cases"]

    if cases_filter:
        filter_ids = [c.strip() for c in cases_filter.split(",")]
        all_cases = [c for c in all_cases if c["id"] in filter_ids]
        print(f"Filtered to {len(all_cases)} cases: {[c['id'] for c in all_cases]}")

    print("=" * 70)
    print("QWEN3-8B BASELINE CAPABILITY BENCHMARK")
    print(f"Total benchmark cases: {len(all_cases)}")
    print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print("=" * 70)

    # Load Model once
    model_path = "./models/Qwen3-8B"
    print("\n[INIT] Loading Qwen3-8B in 4-bit...")
    t0_load = time.time()
    model, tokenizer = load_model(model_path, quantization="4bit")
    load_time = time.time() - t0_load
    print(f"[INIT] Model loaded in {load_time:.2f}s\n")

    if run_dir_arg:
        run_dir = Path(run_dir_arg)
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        run_dir = BENCHMARK_DIR / "results" / f"run_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=True)

    # Define execution modes
    modes = []
    if mode_arg in ("A", "both"):
        modes.append({
            "name": "MODE_A_THINKING_OFF",
            "thinking": False,
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 20,
            "max_new_tokens": 900,
            "subfolder": run_dir / "mode_a_thinking_off"
        })
    if mode_arg in ("B", "both"):
        modes.append({
            "name": "MODE_B_THINKING_ON",
            "thinking": True,
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 40,
            "max_new_tokens": 1400,
            "subfolder": run_dir / "mode_b_thinking_on"
        })

    all_results = []

    for mode in modes:
        mode_name = mode["name"]
        thinking_flag = mode["thinking"]
        mode_dir = mode["subfolder"]
        mode_dir.mkdir(parents=True, exist_ok=True)

        print("\n" + "#" * 70)
        print(f"STARTING {mode_name} (Thinking: {thinking_flag}, Temp: {mode['temperature']}, Top-P: {mode['top_p']})")
        print("#" * 70)

        for idx, case in enumerate(all_cases, 1):
            case_id = case["id"]
            cap = case["capability"]
            diff = case["difficulty"]
            title = case["title"]
            case_file = mode_dir / f"{case_id}.json"

            # Resume check if case already exists and completed successfully
            if case_file.exists():
                try:
                    with open(case_file) as f_existing:
                        existing_record = json.load(f_existing)
                    if existing_record.get("status") == "ok":
                        print(f"[{idx:02d}/{len(all_cases):02d}] {mode_name} | {case_id} ({diff}) [RESUMED/CACHED] -> {existing_record.get('tokens_generated')} tokens in {existing_record.get('generation_time')}s")
                        all_results.append(existing_record)
                        continue
                except Exception:
                    pass

            print(f"[{idx:02d}/{len(all_cases):02d}] {mode_name} | {case_id} ({diff}) - {title[:40]}...", end="", flush=True)

            prompt = build_prompt_for_case(case)
            messages = [{"role": "user", "content": prompt}]
            rendered = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
                enable_thinking=thinking_flag
            )

            status = "ok"
            error_msg = None
            raw_output = ""
            gen_time = 0.0
            tokens_generated = 0
            tokens_per_sec = 0.0

            t0_gen = time.time()
            try:
                inputs = tokenizer(rendered, return_tensors="pt").to(model.device)
                prompt_len = inputs["input_ids"].shape[1]

                gen_kwargs = {
                    "max_new_tokens": mode["max_new_tokens"],
                    "pad_token_id": tokenizer.pad_token_id or tokenizer.eos_token_id,
                }
                if mode["temperature"] > 0:
                    gen_kwargs.update({
                        "do_sample": True,
                        "temperature": mode["temperature"],
                        "top_p": mode["top_p"],
                        "top_k": mode["top_k"],
                    })
                else:
                    gen_kwargs["do_sample"] = False

                with torch.no_grad():
                    out = model.generate(**inputs, **gen_kwargs)

                gen_time = time.time() - t0_gen
                new_tokens = out[0][prompt_len:]
                tokens_generated = int(new_tokens.shape[0])
                tokens_per_sec = round(tokens_generated / max(gen_time, 0.001), 2)
                raw_output = tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

            except Exception as e:
                gen_time = time.time() - t0_gen
                status = "error"
                error_msg = f"{type(e).__name__}: {str(e)}"
                print(f" FAILED! {error_msg}")

            record = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": "Qwen3-8B",
                "model_path": model_path,
                "quantization": "4-bit NF4",
                "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
                "mode": mode_name,
                "thinking_mode": thinking_flag,
                "capability": cap,
                "case_id": case_id,
                "difficulty": diff,
                "title": title,
                "prompt": prompt,
                "rendered_prompt": rendered,
                "raw_output": raw_output,
                "temperature": mode["temperature"],
                "top_p": mode["top_p"],
                "top_k": mode["top_k"],
                "max_new_tokens": mode["max_new_tokens"],
                "generation_time": round(gen_time, 2),
                "tokens_generated": tokens_generated,
                "tokens_per_sec": tokens_per_sec,
                "status": status,
                "error": error_msg,
                "expected_focus": case.get("expected_focus", ""),
                "evaluation_points": case.get("evaluation_points", []),
            }

            all_results.append(record)

            # Save individual record immediately
            case_file = mode_dir / f"{case_id}.json"
            with open(case_file, "w") as f_out:
                json.dump(record, f_out, indent=2)

            if status == "ok":
                print(f" -> {tokens_generated} tokens in {gen_time:.1f}s ({tokens_per_sec} t/s)")

    # Save summary
    summary_file = run_dir / "benchmark_summary.json"
    summary_data = {
        "run_id": f"run_{timestamp}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": "Qwen3-8B",
        "quantization": "4-bit NF4",
        "total_executions": len(all_results),
        "results": all_results,
    }
    with open(summary_file, "w") as f:
        json.dump(summary_data, f, indent=2)

    # Generate Markdown Summary Table
    md_summary = generate_summary_markdown(all_results, run_dir)
    print("\n" + "=" * 70)
    print(f"BENCHMARK COMPLETED! All results saved to:\n{run_dir}")
    print("=" * 70)
    print(md_summary)

    # Update latest symlink / file
    latest_file = BENCHMARK_DIR / "results" / "latest_run.txt"
    latest_file.write_text(str(run_dir))

    return run_dir


def generate_summary_markdown(results: list, run_dir: Path) -> str:
    """Generates the required summary comparison table."""
    caps = ["Unit Test Generation", "Integration Test Generation", "MISRA / Static Analysis", "Regression Suite Upkeep"]
    
    lines = [
        "# Qwen3-8B Baseline Benchmark Summary",
        f"**Run ID**: `{run_dir.name}` | **Model**: `Qwen3-8B (4-bit NF4)`",
        "",
        "### Generation Performance Breakdown",
        "| Capability | Mode | Cases | Success | Failed | Avg Tokens | Avg Time (s) | Avg Tokens/s |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for cap in caps:
        for mode in ("MODE_A_THINKING_OFF", "MODE_B_THINKING_ON"):
            mode_label = "Thinking OFF" if "OFF" in mode else "Thinking ON"
            subset = [r for r in results if r["capability"] == cap and r["mode"] == mode]
            if not subset:
                continue
            total = len(subset)
            success = sum(1 for r in subset if r["status"] == "ok")
            failed = total - success
            avg_tok = round(sum(r["tokens_generated"] for r in subset) / max(total, 1), 1)
            avg_time = round(sum(r["generation_time"] for r in subset) / max(total, 1), 2)
            avg_speed = round(sum(r["tokens_per_sec"] for r in subset) / max(total, 1), 2)
            lines.append(f"| {cap} | {mode_label} | {total} | {success} | {failed} | {avg_tok} | {avg_time}s | {avg_speed} t/s |")

    # Overall summary
    lines.append("")
    lines.append("### Overall Mode Comparison")
    lines.append("| Mode | Total Generations | Success | Failed | Avg Generation Time | Avg Speed |")
    lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")

    for mode in ("MODE_A_THINKING_OFF", "MODE_B_THINKING_ON"):
        mode_label = "Thinking OFF" if "OFF" in mode else "Thinking ON"
        subset = [r for r in results if r["mode"] == mode]
        if not subset:
            continue
        total = len(subset)
        success = sum(1 for r in subset if r["status"] == "ok")
        failed = total - success
        avg_time = round(sum(r["generation_time"] for r in subset) / max(total, 1), 2)
        avg_speed = round(sum(r["tokens_per_sec"] for r in subset) / max(total, 1), 2)
        lines.append(f"| {mode_label} | {total} | {success} | {failed} | {avg_time}s | {avg_speed} t/s |")

    md_text = "\n".join(lines)
    (run_dir / "summary_report.md").write_text(md_text)

    # Automatically generate human evaluation template
    try:
        from evaluate_results import create_evaluation_template
        create_evaluation_template(run_dir)
    except Exception as e:
        print(f"Note: Could not auto-generate evaluation template: {e}")

    return md_text


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Qwen3-8B Baseline Benchmark")
    parser.add_argument("--mode", choices=["A", "B", "both"], default="both", help="Mode A (off), Mode B (on), or both")
    parser.add_argument("--cases", type=str, default=None, help="Comma-separated case IDs to run")
    parser.add_argument("--run-dir", type=str, default=None, help="Path to existing or specific run directory (for resume)")
    args = parser.parse_args()

    run_benchmark(mode_arg=args.mode, cases_filter=args.cases, run_dir_arg=args.run_dir)

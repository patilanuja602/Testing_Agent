#!/usr/bin/env python3
"""
Repeatability and Consistency Runner for Qwen2.5-Coder-7B
Evaluates C-01, CPP-01, and C-04 across 3 seeds (42, 101, 202) at temp 0.2
"""
import os
import subprocess
import time
import json
import re
import csv
from pathlib import Path
from run_audit_experiments import BENCHMARK_PROMPTS, clean_code, compile_and_test, run_single_inference

BASE_DIR = Path("/home/gitadmin/Documents/Anuja")
AUDIT_DIR = BASE_DIR / "model_audit"
ANALYSIS_DIR = AUDIT_DIR / "analysis"

TARGET_FUNCS = ["C-01", "CPP-01", "C-04"]
SEEDS = [42, 101, 202]

def run_repeatability():
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    
    print("Starting Repeatability Evaluation...")
    for func_id in TARGET_FUNCS:
        prompt_data = BENCHMARK_PROMPTS[func_id]
        for run_idx, seed in enumerate(SEEDS, start=1):
            print(f"Testing {func_id} - Run {run_idx} (Seed {seed})...")
            raw_out, stderr, perf = run_single_inference(func_id, prompt_data, seed=seed, temp=0.2)
            clean_t = clean_code(raw_out, prompt_data["language"])
            
            # Count assert statements in clean code
            assert_count = len(re.findall(r"\bassert\s*\(", clean_t))
            
            # Temporarily save and test
            test_res = compile_and_test(f"{func_id}_rep_{seed}", prompt_data, clean_t)
            
            results.append({
                "function_id": func_id,
                "run_id": f"Run-{run_idx}",
                "seed": seed,
                "temperature": 0.2,
                "test_count": assert_count,
                "compile_success": test_res["compile_success"],
                "exec_success": test_res["exec_success"],
                "exec_rc": test_res["exec_rc"],
                "line_coverage": test_res["line_coverage"],
                "branch_coverage": test_res["branch_coverage"],
                "eval_speed_ts": perf["eval_speed_ts"],
                "wall_time_sec": perf["wall_time_sec"]
            })
            print(f"  Asserts: {assert_count}, Compile: {test_res['compile_success']}, Exec: {test_res['exec_success']}, Lines: {test_res['line_coverage']}%, Branches: {test_res['branch_coverage']}%")

    out_csv = ANALYSIS_DIR / "repeatability_analysis.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"Repeatability analysis written to {out_csv}")

if __name__ == "__main__":
    run_repeatability()

#!/usr/bin/env python3
"""
Mutation testing evaluation for C-01 (sensor_raw_valid) and CPP-01 (Account::withdraw)
"""
import os
import subprocess
import json
from pathlib import Path

BASE_DIR = Path("/home/gitadmin/Documents/Anuja")
AUDIT_DIR = BASE_DIR / "model_audit"
EXPERIMENTS_DIR = AUDIT_DIR / "experiments"
GEN_TESTS_DIR = EXPERIMENTS_DIR / "generated_tests"
MUTATION_DIR = EXPERIMENTS_DIR / "mutation"

C_PROJECT_DIR = BASE_DIR / "benchmark_projects" / "sensor_monitoring_c"
CPP_PROJECT_DIR = BASE_DIR / "benchmark_projects" / "banking_transactions_cpp"

def run_mutation_tests():
    MUTATION_DIR.mkdir(parents=True, exist_ok=True)
    results = {}

    # --- C-01 Mutations ---
    c_src_orig = (C_PROJECT_DIR / "src" / "sensor_monitoring.c").read_text()
    c_test_file = GEN_TESTS_DIR / "test_C-01.c"
    
    if c_test_file.exists():
        c_mutants = {
            "C-01_M1_boundary_min": c_src_orig.replace("if (raw_adc < SENSOR_RAW_MIN)", "if (raw_adc <= SENSOR_RAW_MIN)"),
            "C-01_M2_boundary_max": c_src_orig.replace("if (raw_adc > SENSOR_RAW_MAX)", "if (raw_adc >= SENSOR_RAW_MAX)"),
            "C-01_M3_inverted_logic": c_src_orig.replace("return true;", "return false;"),
            "C-01_M4_always_true": c_src_orig.replace("if (raw_adc < SENSOR_RAW_MIN) {\n        return false;\n    }", "/* deleted check */")
        }
        
        c_results = {}
        for m_name, m_code in c_mutants.items():
            m_src = MUTATION_DIR / f"{m_name}.c"
            m_src.write_text(m_code)
            bin_file = Path(f"/tmp/bin_{m_name}")
            
            cmd_comp = [
                "gcc", "-O0", "-g",
                f"-I{C_PROJECT_DIR}/include",
                str(c_test_file),
                str(m_src),
                "-o", str(bin_file),
                "-lm"
            ]
            res_comp = subprocess.run(cmd_comp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res_comp.returncode != 0:
                c_results[m_name] = {"status": "COMPILE_ERROR", "log": res_comp.stderr}
            else:
                res_exec = subprocess.run([str(bin_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                # If test assertions fail (SIGABRT/rc != 0), the mutant was detected/killed!
                if res_exec.returncode != 0:
                    c_results[m_name] = {"status": "KILLED", "exit_code": res_exec.returncode, "log": res_exec.stderr}
                else:
                    c_results[m_name] = {"status": "SURVIVED", "exit_code": 0, "log": "Test passed despite mutant"}
        results["C-01"] = c_results

    # --- CPP-01 Mutations ---
    cpp_src_orig = (CPP_PROJECT_DIR / "src" / "banking_transactions.cpp").read_text()
    cpp_test_file = GEN_TESTS_DIR / "test_CPP-01.cpp"
    
    if cpp_test_file.exists():
        # Mutant 1: swap daily limit check before balance check
        m1_code = cpp_src_orig.replace(
"""    if (amount > balance_) {
        return WithdrawResult::INSUFFICIENT_FUNDS;
    }
    if (daily_withdrawn_ + amount > daily_limit_) {
        return WithdrawResult::DAILY_LIMIT_EXCEEDED;
    }""",
"""    if (daily_withdrawn_ + amount > daily_limit_) {
        return WithdrawResult::DAILY_LIMIT_EXCEEDED;
    }
    if (amount > balance_) {
        return WithdrawResult::INSUFFICIENT_FUNDS;
    }"""
        )
        # Mutant 2: off-by-one daily limit check (>= instead of >)
        m2_code = cpp_src_orig.replace("daily_withdrawn_ + amount > daily_limit_", "daily_withdrawn_ + amount >= daily_limit_")
        # Mutant 3: omit balance deduction
        m3_code = cpp_src_orig.replace("balance_ -= amount;", "// omitted deduction")
        
        cpp_mutants = {
            "CPP-01_M1_order_precedence": m1_code,
            "CPP-01_M2_boundary_ge": m2_code,
            "CPP-01_M3_omitted_deduction": m3_code
        }
        
        cpp_results = {}
        for m_name, m_code in cpp_mutants.items():
            m_src = MUTATION_DIR / f"{m_name}.cpp"
            m_src.write_text(m_code)
            bin_file = Path(f"/tmp/bin_{m_name}")
            
            cmd_comp = [
                "g++", "-std=c++17", "-O0", "-g",
                f"-I{CPP_PROJECT_DIR}/include",
                str(cpp_test_file),
                str(m_src),
                "-o", str(bin_file)
            ]
            res_comp = subprocess.run(cmd_comp, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res_comp.returncode != 0:
                cpp_results[m_name] = {"status": "COMPILE_ERROR", "log": res_comp.stderr}
            else:
                res_exec = subprocess.run([str(bin_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res_exec.returncode != 0:
                    cpp_results[m_name] = {"status": "KILLED", "exit_code": res_exec.returncode, "log": res_exec.stderr}
                else:
                    cpp_results[m_name] = {"status": "SURVIVED", "exit_code": 0, "log": "Test passed despite mutant"}
        results["CPP-01"] = cpp_results

    out_file = MUTATION_DIR / "mutation_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print("Mutation results written to", out_file)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    run_mutation_tests()

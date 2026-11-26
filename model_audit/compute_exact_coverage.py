#!/usr/bin/env python3
"""
Compute exact per-function line and branch coverage using gcov
"""
import os
import subprocess
import re
import csv
import shutil
from pathlib import Path

BASE_DIR = Path("/home/gitadmin/Documents/Anuja")
AUDIT_DIR = BASE_DIR / "model_audit"
EXPERIMENTS_DIR = AUDIT_DIR / "experiments"
GEN_TESTS_DIR = EXPERIMENTS_DIR / "generated_tests"
COVERAGE_DIR = EXPERIMENTS_DIR / "coverage"
ANALYSIS_DIR = AUDIT_DIR / "analysis"

C_PROJECT_DIR = BASE_DIR / "benchmark_projects" / "sensor_monitoring_c"
CPP_PROJECT_DIR = BASE_DIR / "benchmark_projects" / "banking_transactions_cpp"

FUNCTION_RANGES = {
    # C benchmark: src/sensor_monitoring.c
    "C-01": (4, 12, "sensor_raw_valid"),
    "C-02": (15, 25, "sensor_scale_temperature"),
    "C-03": (28, 41, "sensor_battery_soc_eval"),
    "C-04": (44, 52, "sensor_pressure_window_check"),
    "C-05": (55, 67, "sensor_can_frame_validate"),
    "C-06": (70, 92, "sensor_uart_crc16_verify"),
    "C-07": (95, 108, "sensor_transient_error_filter"),
    "C-08": (111, 122, "sensor_circular_buffer_push"),
    "C-09": (125, 153, "sensor_calibration_lookup"),
    "C-10": (156, 193, "sensor_fsm_step"),
    # C++ benchmark: src/banking_transactions.cpp
    "CPP-01": (10, 23, "Account::withdraw"),
    "CPP-02": (25, 34, "Account::deposit"),
    "CPP-03": (36, 51, "Account::transfer_to"),
    "CPP-04": (58, 65, "InterestCalculator::calculate_accrued"),
    "CPP-05": (69, 78, "TransactionLogger::log_transaction"),
    "CPP-06": (83, 97, "SecurityManager::authenticate"),
    "CPP-07": (102, 110, "SessionToken::is_valid"),
    "CPP-08": (126, 139, "CurrencyConverter::convert"),
    "CPP-09": (141, 159, "FeeSchedule::calculate_fee"),
    "CPP-10": (170, 186, "AuditTrail::verify_integrity"),
}

MANIFEST_FILE = AUDIT_DIR / "dataset" / "evaluation_manifest.csv"

def compute_coverage():
    COVERAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(MANIFEST_FILE, "r") as f:
        reader = csv.DictReader(f)
        manifest = list(reader)
        
    coverage_results = []
    
    for row in manifest:
        func_id = row["function_id"]
        lang = row["language"]
        sig = row["signature"]
        start_line, end_line, func_name = FUNCTION_RANGES[func_id]
            
        ext = "c" if lang == "C" else "cpp"
        test_file = GEN_TESTS_DIR / f"test_{func_id}.{ext}"
        if not test_file.exists():
            continue
            
        work_dir = Path(f"/tmp/cov_build_{func_id}")
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
        
        src_file = C_PROJECT_DIR / "src" / "sensor_monitoring.c" if lang == "C" else CPP_PROJECT_DIR / "src" / "banking_transactions.cpp"
        inc_dir = C_PROJECT_DIR / "include" if lang == "C" else CPP_PROJECT_DIR / "include"
        
        shutil.copy(src_file, work_dir / src_file.name)
        shutil.copy(test_file, work_dir / test_file.name)
        
        bin_file = work_dir / f"bin_{func_id}"
        
        if lang == "C":
            cmd = ["gcc", "-O0", "-g", "-fprofile-arcs", "-ftest-coverage", f"-I{inc_dir}", str(work_dir / test_file.name), str(work_dir / src_file.name), "/tmp/gcov_handler.o", "-o", str(bin_file), "-lm"]
        else:
            cmd = ["g++", "-std=c++17", "-O0", "-g", "-fprofile-arcs", "-ftest-coverage", f"-I{inc_dir}", str(work_dir / test_file.name), str(work_dir / src_file.name), "/tmp/gcov_handler.o", "-o", str(bin_file)]
            
        res_comp = subprocess.run(cmd, cwd=str(work_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        compile_pass = (res_comp.returncode == 0)
        exec_pass = False
        func_line_cov = 0.0
        func_branch_cov = 0.0
        lines_total = 0
        lines_exec = 0
        branches_total = 0
        branches_exec = 0
        
        if compile_pass:
            res_exec = subprocess.run([str(bin_file)], cwd=str(work_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            exec_pass = (res_exec.returncode == 0)
            
            # Run gcov pointing to the object .gcno file
            gcno_file = f"bin_{func_id}-{src_file.stem}.gcno"
            cmd_gcov = ["gcov", "-b", "-c", gcno_file]
            res_gcov = subprocess.run(cmd_gcov, cwd=str(work_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            gcov_file = work_dir / f"{src_file.name}.gcov"
            if gcov_file.exists():
                gcov_content = gcov_file.read_text()
                
                # Copy to COVERAGE_DIR
                (COVERAGE_DIR / f"{func_id}_{src_file.name}.gcov").write_text(gcov_content)
                
                # Scan lines between start_line and end_line
                cur_line_no = 0
                for line in gcov_content.splitlines():
                    # Format: "execution_count: line_number:source_code"
                    parts = line.split(":", 2)
                    if len(parts) >= 2:
                        try:
                            lno = int(parts[1].strip())
                            cur_line_no = lno
                        except ValueError:
                            pass
                            
                    if start_line <= cur_line_no <= end_line:
                        if len(parts) >= 3 and parts[1].strip().isdigit():
                            count_str = parts[0].strip()
                            if count_str.isdigit():
                                lines_total += 1
                                if int(count_str) > 0:
                                    lines_exec += 1
                            elif count_str == "#####":
                                lines_total += 1
                        if "branch " in line:
                            branches_total += 1
                            if "taken 0" not in line and "never executed" not in line:
                                branches_exec += 1
                                
                if lines_total > 0:
                    func_line_cov = round((lines_exec / lines_total) * 100.0, 1)
                if branches_total > 0:
                    func_branch_cov = round((branches_exec / branches_total) * 100.0, 1)
                    
        coverage_results.append({
            "func_id": func_id,
            "language": lang,
            "signature": sig,
            "func_name": func_name,
            "compile_pass": compile_pass,
            "exec_pass": exec_pass,
            "lines_executed": lines_exec,
            "lines_total": lines_total,
            "line_coverage_pct": func_line_cov,
            "branches_executed": branches_exec,
            "branches_total": branches_total,
            "branch_coverage_pct": func_branch_cov
        })
        print(f"{func_id:6s} | {func_name:30s} | Comp:{'PASS' if compile_pass else 'FAIL':4s} | Exec:{'PASS' if exec_pass else 'FAIL':4s} | Lines: {lines_exec:2d}/{lines_total:2d} ({func_line_cov:5.1f}%) | Branches: {branches_exec:2d}/{branches_total:2d} ({func_branch_cov:5.1f}%)")

    out_csv = ANALYSIS_DIR / "per_function_coverage.csv"
    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(coverage_results[0].keys()))
        writer.writeheader()
        writer.writerows(coverage_results)
    print("\nExact per-function coverage successfully written to", out_csv)

if __name__ == "__main__":
    compute_coverage()

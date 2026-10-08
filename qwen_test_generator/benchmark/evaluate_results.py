"""Human evaluation workflow tool for reviewing and scoring benchmark outputs."""
import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

BENCHMARK_DIR = Path(__file__).resolve().parent

FAILURE_TAXONOMY = [
    "missed_requirement",
    "incomplete_coverage",
    "incorrect_test",
    "incorrect_expected_result",
    "invented_requirement",
    "invented_threshold",
    "unsupported_assumption",
    "duplicate_test",
    "weak_integration_reasoning",
    "weak_state_reasoning",
    "weak_failure_reasoning",
    "incorrect_misra_reasoning",
    "unsupported_false_positive_claim",
    "weak_remediation",
    "weak_regression_impact_analysis",
    "excessive_generic_output"
]

CAPABILITY_DIMENSIONS = {
    "Unit Test Generation": [
        "requirement_understanding",
        "requirement_coverage",
        "positive_coverage",
        "negative_coverage",
        "boundary_coverage",
        "expected_result_correctness",
        "traceability",
        "logical_correctness",
        "unsupported_assumption_avoidance",
        "practical_usefulness"
    ],
    "Integration Test Generation": [
        "component_identification",
        "interface_understanding",
        "sequence_correctness",
        "data_flow_coverage",
        "failure_path_coverage",
        "recovery_coverage",
        "expected_result_quality",
        "traceability",
        "logical_correctness",
        "practical_usefulness"
    ],
    "MISRA / Static Analysis": [
        "finding_comprehension",
        "rule_context_understanding",
        "code_reasoning",
        "risk_reasoning",
        "remediation_quality",
        "uncertainty_handling",
        "avoidance_of_invented_policy",
        "test_impact_reasoning",
        "technical_usefulness",
        "human_review_awareness"
    ],
    "Regression Suite Upkeep": [
        "change_understanding",
        "affected_test_identification",
        "tests_to_add_reasoning",
        "tests_to_modify_reasoning",
        "obsolete_test_identification",
        "traceability",
        "dependency_reasoning",
        "coverage_preservation",
        "logical_correctness",
        "practical_usefulness"
    ]
}


def create_evaluation_template(run_dir_path: Path):
    """Generates a structured human evaluation template for all benchmark outputs in a run."""
    summary_file = run_dir_path / "benchmark_summary.json"
    if not summary_file.exists():
        raise FileNotFoundError(f"Run summary not found at {summary_file}")

    with open(summary_file, "r") as f:
        run_data = json.load(f)

    results = run_data["results"]
    eval_records = []

    for r in results:
        cap = r["capability"]
        dims = CAPABILITY_DIMENSIONS.get(cap, [])
        record = {
            "case_id": r["case_id"],
            "capability": cap,
            "mode": r["mode"],
            "difficulty": r["difficulty"],
            "title": r["title"],
            "dimension_scores": {d: None for d in dims},
            "total_score": None,
            "outcome": None,  # "PASS", "PARTIAL", "FAIL"
            "failure_types": [],  # Subset of FAILURE_TAXONOMY
            "evaluator": None,
            "evaluation_timestamp": None,
            "notes": ""
        }
        eval_records.append(record)

    template_file = run_dir_path / "human_evaluation_template.json"
    with open(template_file, "w") as f:
        json.dump({
            "run_id": run_data.get("run_id", run_dir_path.name),
            "instructions": (
                "For each record, enter scores 0-10 for each dimension in dimension_scores. "
                "Total score is sum of dimensions (0-100). "
                "Outcome: 80-100 = PASS, 50-79 = PARTIAL, 0-49 = FAIL. "
                "Tag any applicable failure_types from standard taxonomy. Add qualitative notes."
            ),
            "valid_failure_types": FAILURE_TAXONOMY,
            "evaluations": eval_records
        }, f, indent=2)

    print(f"Created human evaluation template with {len(eval_records)} entries at:\n{template_file}")
    return template_file


def summarize_evaluations(eval_file_path: Path):
    """Summarizes human evaluation scores across capabilities and modes."""
    with open(eval_file_path, "r") as f:
        data = json.load(f)

    evals = data.get("evaluations", [])
    completed = [e for e in evals if e.get("total_score") is not None]

    print("=" * 70)
    print("HUMAN EVALUATION AUDIT SUMMARY")
    print(f"Total Cases: {len(evals)} | Completed Reviews: {len(completed)}")
    print("=" * 70)

    if not completed:
        print("No cases have been scored yet. Use human_evaluation_template.json to record scores.")
        return

    caps = list(CAPABILITY_DIMENSIONS.keys())
    modes = ["MODE_A_THINKING_OFF", "MODE_B_THINKING_ON"]

    for cap in caps:
        print(f"\n--- {cap} ---")
        for mode in modes:
            sub = [e for e in completed if e["capability"] == cap and e["mode"] == mode]
            if not sub:
                continue
            scores = [e["total_score"] for e in sub]
            avg_score = round(sum(scores) / len(scores), 1)
            pass_count = sum(1 for e in sub if e.get("outcome") == "PASS")
            part_count = sum(1 for e in sub if e.get("outcome") == "PARTIAL")
            fail_count = sum(1 for e in sub if e.get("outcome") == "FAIL")
            print(f"  {mode}: Scored {len(sub)}/{len([e for e in evals if e['capability'] == cap and e['mode'] == mode])} | Avg: {avg_score}/100 | PASS: {pass_count}, PARTIAL: {part_count}, FAIL: {fail_count}")

    # Failure types tally
    failures_tally = {}
    for e in completed:
        for f_tag in e.get("failure_types", []):
            failures_tally[f_tag] = failures_tally.get(f_tag, 0) + 1

    if failures_tally:
        print("\nIdentified Failure Types:")
        for k, v in sorted(failures_tally.items(), key=lambda x: -x[1]):
            print(f"  - {k}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Human Evaluation Workflow Tool")
    parser.add_argument("--run-dir", type=str, default=None, help="Path to benchmark run directory")
    parser.add_argument("--create-template", action="store_true", help="Create evaluation template")
    parser.add_argument("--summarize", type=str, default=None, help="Path to completed evaluation JSON")
    args = parser.parse_args()

    if args.create_template:
        target_dir = Path(args.run_dir) if args.run_dir else Path(BENCHMARK_DIR / "results" / "latest_run.txt").read_text().strip()
        create_evaluation_template(Path(target_dir))
    elif args.summarize:
        summarize_evaluations(Path(args.summarize))
    else:
        parser.print_help()


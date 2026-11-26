#!/usr/bin/env python3
"""
Generate capability scorecard, failure register, and RAG gap analysis CSVs
"""
import csv
from pathlib import Path

ANALYSIS_DIR = Path("/home/gitadmin/Documents/Anuja/model_audit/analysis")
ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

# 1. Capability Scorecard
# Measures the model across 10 core capability dimensions
SCORECARD_DATA = [
    {
        "dimension_id": "DIM-01",
        "capability_dimension": "Explicit Requirement Understanding",
        "description": "Preservation and adherence to explicitly stated functional rules and constraints",
        "score_out_of_10": 8.0,
        "grade": "B",
        "empirical_findings": "Accurately extracted explicitly documented status enums, ranges, and error return constants in 16/20 cases; struggled with explicit capacity eviction rules (CPP-05)."
    },
    {
        "dimension_id": "DIM-02",
        "capability_dimension": "Implicit Scenario Discovery",
        "description": "Ability to identify unspecified edge cases, empty inputs, null pointers, and wraparounds",
        "score_out_of_10": 6.5,
        "grade": "C+",
        "empirical_findings": "Discovered null pointer checks and standard negative inputs well, but missed complex sequence gaps, modulo overflow edge cases, and multi-party rollback scenarios."
    },
    {
        "dimension_id": "DIM-03",
        "capability_dimension": "Logical Invariant Reasoning",
        "description": "Reasoning about conservation laws, monotonic counters, cryptographic chains, and state preservation",
        "score_out_of_10": 4.0,
        "grade": "D",
        "empirical_findings": "Consistently broke stateful invariants across sequential calls (CPP-01 balance depletion, C-05 counter advancing, CPP-10 hash link pointer chaining)."
    },
    {
        "dimension_id": "DIM-04",
        "capability_dimension": "Boundary Value Analysis",
        "description": "Evaluation of minimum, maximum, just below, just above, and off-by-one values",
        "score_out_of_10": 8.5,
        "grade": "B+",
        "empirical_findings": "Strongest dimension. Accurately targeted 0, 4095, -1, 4096 in C-01, [10.0, 150.0] in C-04, and LONG_MAX in CPP-02."
    },
    {
        "dimension_id": "DIM-05",
        "capability_dimension": "Negative & Fault-Handling Testing",
        "description": "Testing invalid parameters, hardware faults, emergency stops, and error return codes",
        "score_out_of_10": 7.5,
        "grade": "B-",
        "empirical_findings": "Generated negative error code assertions across all functions; however, execution path errors frequently masked the intended error branch (C-09 NULL before empty)."
    },
    {
        "dimension_id": "DIM-06",
        "capability_dimension": "Expected-Result Correctness & Evidence Discipline",
        "description": "Truthfulness of expected assertions and resistance to calculation hallucinations",
        "score_out_of_10": 3.5,
        "grade": "F",
        "empirical_findings": "Severe hallucination of expected values: fabricated CRC-16 (C-06), 10x interest formula error (CPP-04), temperature scale hallucination (C-02), and double/long fee confusion (CPP-09)."
    },
    {
        "dimension_id": "DIM-07",
        "capability_dimension": "Code Quality & Compile Readiness",
        "description": "Syntactic validity, standards compliance, proper includes, and compilation success",
        "score_out_of_10": 9.0,
        "grade": "A-",
        "empirical_findings": "18/20 (90%) tests compiled cleanly under strict GCC/G++ -O0 -g -Wall. Only 2 compilation failures (CPP-03 mock inheritance, CPP-08 missing <cmath>)."
    },
    {
        "dimension_id": "DIM-08",
        "capability_dimension": "Coverage Achievement",
        "description": "Line and branch coverage achieved on targeted functions",
        "score_out_of_10": 8.0,
        "grade": "B",
        "empirical_findings": "Achieved 100% line coverage on 12/20 functions and >85% on 16/20 functions. However, coverage was decoupled from test pass rate (high coverage with failed asserts)."
    },
    {
        "dimension_id": "DIM-09",
        "capability_dimension": "Mutation Detection",
        "description": "Ability of passing test suites to detect and kill seeded code mutations",
        "score_out_of_10": 9.0,
        "grade": "A-",
        "empirical_findings": "On valid passing test suites (C-01), killed 4/4 mutants (100% mutation score) including boundary shifts, inverted logic, and deleted guards."
    },
    {
        "dimension_id": "DIM-10",
        "capability_dimension": "Repeatability & Consistency",
        "description": "Stability of test structure and outcomes across multiple seeds",
        "score_out_of_10": 8.5,
        "grade": "B+",
        "empirical_findings": "Stateless functions (C-01, C-04) produced 100% consistent passing test suites across seeds. Stateful functions (CPP-01) consistently failed across 100% of seeds."
    }
]

# 2. Failure Register
# Every failure observed in the 20 benchmark runs classified under F01-F15
FAILURE_REGISTER_DATA = [
    {
        "failure_id": "FAIL-01",
        "function_id": "C-02",
        "function_signature": "int sensor_scale_temperature(int raw_adc, float *temp_c)",
        "failure_code": "F04",
        "failure_name": "Assertion failure on valid code (wrong expected outcome)",
        "root_cause_description": "Hallucinated expected temperature value: asserted temp_c == 0.0f at raw_adc=4095 instead of 289.65 C, and 24.0f at raw_adc=2048 instead of 124.86 C.",
        "compiler_or_runtime_error": "Assertion `fabsf(temp_c - 0.0f) < EPSILON' failed. rc=-6",
        "rag_category": "R08",
        "rag_relevance_notes": "Requires exact domain formula calculation or golden test vectors from design specification."
    },
    {
        "failure_id": "FAIL-02",
        "function_id": "C-05",
        "function_signature": "int sensor_can_frame_validate(uint16_t id, uint8_t dlc, uint8_t counter, uint8_t last_counter)",
        "failure_code": "F10",
        "failure_name": "State / sequence error (incorrect preconditions or test order)",
        "root_cause_description": "Misunderstood rolling alive counter invariant; passed counter=0 with last_counter=0 expecting SENSOR_OK, but formula requires counter == (last+1)&0x0F.",
        "compiler_or_runtime_error": "Assertion `sensor_can_frame_validate(0x2F0, 8, 0, 0) == SENSOR_OK' failed. rc=-6",
        "rag_category": "R05",
        "rag_relevance_notes": "Requires sequence and state transition rules specifying rolling alive counter behavior."
    },
    {
        "failure_id": "FAIL-03",
        "function_id": "C-06",
        "function_signature": "int sensor_uart_crc16_verify(const uint8_t *payload, uint8_t len, uint16_t expected_crc)",
        "failure_code": "F04",
        "failure_name": "Assertion failure on valid code (wrong expected outcome)",
        "root_cause_description": "Hallucinated CRC-16 checksum 0x1234 for payload {0x01,0x02,0x03,0x04}; LLMs cannot compute non-trivial polynomials without external oracle.",
        "compiler_or_runtime_error": "Assertion `sensor_uart_crc16_verify(payload2, sizeof(payload2), expected_crc2) == SENSOR_OK' failed. rc=-6",
        "rag_category": "R08",
        "rag_relevance_notes": "Requires precomputed golden CRC vectors or retrieval of verified test vectors."
    },
    {
        "failure_id": "FAIL-04",
        "function_id": "C-08",
        "function_signature": "int sensor_circular_buffer_push(SensorCircularBuffer *buf, uint32_t sample)",
        "failure_code": "F10",
        "failure_name": "State / sequence error (incorrect preconditions or test order)",
        "root_cause_description": "Precondition violation: manually set buf.count = SENSOR_BUF_CAPACITY (8) and asserted that push() would return SENSOR_OK and grow count to 9.",
        "compiler_or_runtime_error": "Assertion `sensor_circular_buffer_push(&buf, sample) == SENSOR_OK' failed. rc=-6",
        "rag_category": "R06",
        "rag_relevance_notes": "Requires structural invariant documentation specifying fixed capacity ring buffer limits."
    },
    {
        "failure_id": "FAIL-05",
        "function_id": "C-09",
        "function_signature": "int sensor_calibration_lookup(float raw_val, const CalibrationPoint *table, size_t table_size, float *calibrated_out)",
        "failure_code": "F05",
        "failure_name": "Execution-path error (wrong branch taken before intended check)",
        "root_cause_description": "Execution path masking: passed table=NULL and table_size=0 intending to test empty table, but NULL guard returned SENSOR_ERR_NULL_PTR before table_size check.",
        "compiler_or_runtime_error": "Assertion `sensor_calibration_lookup(1.5, NULL, 0, &calibrated_out1) == SENSOR_ERR_EMPTY_TABLE' failed. rc=-6",
        "rag_category": "R09",
        "rag_relevance_notes": "Requires branch precedence graph showing NULL checks precede size/boundary checks."
    },
    {
        "failure_id": "FAIL-06",
        "function_id": "C-10",
        "function_signature": "ConveyorState sensor_fsm_step(ConveyorState current_state, MotorCommand cmd, float current_rpm, float target_rpm, bool hardware_fault)",
        "failure_code": "F05",
        "failure_name": "Execution-path error (wrong branch taken before intended check)",
        "root_cause_description": "Failed to account for state machine transition rule: passed current_rpm=100.0f and target_rpm=100.0f from FSM_ACCELERATING expecting to stay in ACCELERATING, but RPM match triggered FSM_RUNNING.",
        "compiler_or_runtime_error": "Assertion `sensor_fsm_step(FSM_ACCELERATING, CMD_NONE, 100.0f, 100.0f, false) == FSM_ACCELERATING' failed. rc=-6",
        "rag_category": "R05",
        "rag_relevance_notes": "Requires complete formal FSM transition matrix and state precondition specification."
    },
    {
        "failure_id": "FAIL-07",
        "function_id": "CPP-01",
        "function_signature": "WithdrawResult Account::withdraw(long amount)",
        "failure_code": "F05",
        "failure_name": "Execution-path error (wrong branch taken before intended check)",
        "root_cause_description": "Historical reproduction confirmed: sequential withdrawals drained balance from 1000 down to 100; subsequent withdraw(200) triggered INSUFFICIENT_FUNDS before DAILY_LIMIT_EXCEEDED could be reached.",
        "compiler_or_runtime_error": "Assertion `account.withdraw(200) == bank::WithdrawResult::DAILY_LIMIT_EXCEEDED' failed. rc=-6",
        "rag_category": "R09",
        "rag_relevance_notes": "Requires branch dependency rules (balance check precedes limit check) and state tracking across sequences."
    },
    {
        "failure_id": "FAIL-08",
        "function_id": "CPP-03",
        "function_signature": "TransferResult Account::transfer_to(Account &destination, long amount)",
        "failure_code": "F08",
        "failure_name": "Mocking / link error (unresolved external symbol or invalid mock)",
        "root_cause_description": "Hallucinated MockAccount subclass with 'override' on withdraw() and deposit(), but Account member functions are non-virtual; also assumed boolean return type.",
        "compiler_or_runtime_error": "error: ‘bool bank::MockAccount::withdraw(long int)’ marked ‘override’, but does not override. rc=1",
        "rag_category": "R07",
        "rag_relevance_notes": "Requires class definition showing whether methods are virtual or non-virtual and mock interface guidelines."
    },
    {
        "failure_id": "FAIL-09",
        "function_id": "CPP-04",
        "function_signature": "double InterestCalculator::calculate_accrued(double principal, double annual_rate, int days)",
        "failure_code": "F04",
        "failure_name": "Assertion failure on valid code (wrong expected outcome)",
        "root_cause_description": "Order of magnitude arithmetic error: calculated interest for principal 1000 at 5% over 365 days as 500.0 instead of 50.0 (10x error).",
        "compiler_or_runtime_error": "Assertion `std::abs(result - 500.0) < 1e-6' failed. rc=-6",
        "rag_category": "R08",
        "rag_relevance_notes": "Requires domain math calculation rules and validated oracle equations."
    },
    {
        "failure_id": "FAIL-09B",
        "function_id": "CPP-05",
        "function_signature": "bool TransactionLogger::log_transaction(const Transaction &tx)",
        "failure_code": "F04",
        "failure_name": "Assertion failure on valid code (wrong expected outcome)",
        "root_cause_description": "Contradicted explicit requirements: prompt specified that when capacity is reached, oldest entry is evicted and transaction is logged (returns true); model asserted false.",
        "compiler_or_runtime_error": "Assertion `!logger2.log_transaction(tx3)' failed. rc=-6",
        "rag_category": "R08",
        "rag_relevance_notes": "Requires retention of explicit contract overrides contrary to common FIFO buffer defaults."
    },
    {
        "failure_id": "FAIL-10",
        "function_id": "CPP-08",
        "function_signature": "long CurrencyConverter::convert(long amount_cents, const std::string &from_curr, const std::string &to_curr) const",
        "failure_code": "F03",
        "failure_name": "Missing include / undefined reference",
        "root_cause_description": "Used std::round without including standard header <cmath>, causing compilation failure under strict standard C++.",
        "compiler_or_runtime_error": "error: ‘round’ is not a member of ‘std’. rc=1",
        "rag_category": "R02",
        "rag_relevance_notes": "Requires include dependency analysis to automatically inject required standard and project headers."
    },
    {
        "failure_id": "FAIL-11",
        "function_id": "CPP-09",
        "function_signature": "long FeeSchedule::calculate_fee(long amount_cents, AccountType type, int monthly_tx_count)",
        "failure_code": "F04",
        "failure_name": "Assertion failure on valid code (wrong expected outcome)",
        "root_cause_description": "Confused percentage representation and return type: wrote 0.5 * 100 * 0.005 (evaluating to 0.25 double) for 0.5% on 100 cents (which truncates to 0 long).",
        "compiler_or_runtime_error": "Assertion `bank::FeeSchedule::calculate_fee(100, bank::AccountType::BUSINESS, 6) == 0.5 * 100 * 0.005' failed. rc=-6",
        "rag_category": "R08",
        "rag_relevance_notes": "Requires business rule specifications detailing currency unit conventions (cents integer vs decimal float)."
    },
    {
        "failure_id": "FAIL-12",
        "function_id": "CPP-10",
        "function_signature": "bool AuditTrail::verify_integrity(const std::vector<TransactionRecord> &records)",
        "failure_code": "F09",
        "failure_name": "Hallucinated function / class / method",
        "root_cause_description": "Redefined mock free functions inside namespace bank rather than testing class AuditTrail; also failed to assign prev_hash link between rec1 and rec2.",
        "compiler_or_runtime_error": "Assertion `bank::verify_integrity({rec1, rec2}) == true' failed. rc=-6",
        "rag_category": "R01",
        "rag_relevance_notes": "Requires exact static class scope resolution and cryptographic data structure initialization patterns."
    }
]

# 3. RAG Gap Analysis
# Maps the 10 RAG requirement categories against the audit findings
RAG_GAP_DATA = [
    {
        "rag_category_id": "R01",
        "rag_requirement_name": "Exact Function Signature & Return Types",
        "failure_count": 2,
        "impact_severity": "HIGH",
        "observed_failure_patterns": "Assumed bool instead of enum class (CPP-03), redefined class methods as namespace free functions (CPP-10).",
        "future_rag_retrieval_specification": "Must retrieve verbatim AST function signature, parameter types, class encapsulation, and return type definitions from headers."
    },
    {
        "rag_category_id": "R02",
        "rag_requirement_name": "Header Dependencies & Include Hierarchy",
        "failure_count": 1,
        "impact_severity": "MEDIUM",
        "observed_failure_patterns": "Missing <cmath> for std::round in CPP-08.",
        "future_rag_retrieval_specification": "Must extract transitive header dependency tree and system header mapping for all standard library symbols used."
    },
    {
        "rag_category_id": "R03",
        "rag_requirement_name": "Valid Input Domains & Range Definitions",
        "failure_count": 1,
        "impact_severity": "MEDIUM",
        "observed_failure_patterns": "Attempted to push sample into full circular buffer (C-08); attempted negative days in interest.",
        "future_rag_retrieval_specification": "Must retrieve hardware specifications, interface control documents (ICDs), and parameter bounds [min, max]."
    },
    {
        "rag_category_id": "R04",
        "rag_requirement_name": "System Error Codes & Exception Types",
        "failure_count": 2,
        "impact_severity": "MEDIUM",
        "observed_failure_patterns": "Confused SENSOR_ERR_NULL_PTR with SENSOR_ERR_EMPTY_TABLE (C-09); confused enum return values.",
        "future_rag_retrieval_specification": "Must retrieve error constant definitions, enum mappings, and thrown exception classes."
    },
    {
        "rag_category_id": "R05",
        "rag_requirement_name": "State-Machine Transitions & Valid Sequences",
        "failure_count": 3,
        "impact_severity": "CRITICAL",
        "observed_failure_patterns": "CAN alive counter sequence mismatch (C-05); FSM RPM transition timing (C-10); Account sequential state depletion (CPP-01).",
        "future_rag_retrieval_specification": "Must retrieve formal state transition diagrams/tables, valid sequence histories, and reset lifecycle requirements."
    },
    {
        "rag_category_id": "R06",
        "rag_requirement_name": "Complex Data Structure Layouts & Invariants",
        "failure_count": 2,
        "impact_severity": "HIGH",
        "observed_failure_patterns": "Circular buffer head/count pointer manipulation (C-08); unlinked cryptographic hash pointers in struct (CPP-10).",
        "future_rag_retrieval_specification": "Must retrieve struct member layout, internal invariants, and canonical factory/setup fixture snippets."
    },
    {
        "rag_category_id": "R07",
        "rag_requirement_name": "Mock/Stub Interfaces & Test Doubles",
        "failure_count": 1,
        "impact_severity": "HIGH",
        "observed_failure_patterns": "Hallucinated inheritance and virtual overrides on non-virtual C++ classes (CPP-03).",
        "future_rag_retrieval_specification": "Must retrieve class inheritance hierarchy, virtuality specifiers, and existing test double fixtures."
    },
    {
        "rag_category_id": "R08",
        "rag_requirement_name": "Domain Invariants, Formulas & Contracts",
        "failure_count": 5,
        "impact_severity": "CRITICAL",
        "observed_failure_patterns": "Hallucinated CRC-16 (C-06); 10x interest formula error (CPP-04); temperature conversion hallucination (C-02); fee percentage math error (CPP-09); sliding window eviction (CPP-05).",
        "future_rag_retrieval_specification": "Must retrieve verified mathematical equations, golden input/output test vectors, and domain business rules."
    },
    {
        "rag_category_id": "R09",
        "rag_requirement_name": "Execution Precedence & Branch Dependencies",
        "failure_count": 3,
        "impact_severity": "CRITICAL",
        "observed_failure_patterns": "Historical Account::withdraw balance before daily limit (CPP-01); NULL check before empty table check (C-09); hardware fault override before command (C-10).",
        "future_rag_retrieval_specification": "Must retrieve branch control-flow graph (CFG) or execution precedence order to prevent early masking."
    },
    {
        "rag_category_id": "R10",
        "rag_requirement_name": "Build Configuration, Compiler Flags & ABI",
        "failure_count": 1,
        "impact_severity": "LOW",
        "observed_failure_patterns": "Missing -lm for math in C; C++17 requirement for nested namespace syntax.",
        "future_rag_retrieval_specification": "Must retrieve CMake/Makefile target flags, required linked libraries, and C/C++ dialect standards."
    }
]

def main():
    # Write Scorecard
    with open(ANALYSIS_DIR / "capability_scorecard.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(SCORECARD_DATA[0].keys()))
        w.writeheader()
        w.writerows(SCORECARD_DATA)
    print("Capability scorecard written to capability_scorecard.csv")

    # Write Failure Register
    with open(ANALYSIS_DIR / "failure_register.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(FAILURE_REGISTER_DATA[0].keys()))
        w.writeheader()
        w.writerows(FAILURE_REGISTER_DATA)
    print("Failure register written to failure_register.csv")

    # Write RAG Gap Analysis
    with open(ANALYSIS_DIR / "rag_gap_analysis.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(RAG_GAP_DATA[0].keys()))
        w.writeheader()
        w.writerows(RAG_GAP_DATA)
    print("RAG gap analysis written to rag_gap_analysis.csv")

if __name__ == "__main__":
    main()

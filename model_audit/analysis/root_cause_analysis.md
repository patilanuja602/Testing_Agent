# Root-Cause Analysis: LLM Failure Modes in C/C++ Unit-Test Generation

**Subject Model**: `Qwen2.5-Coder-7B-Instruct — Q4_K_M GGUF`  
**Evaluation Scope**: 20 C and C++ Embedded & Banking Functions  
**Compiler Infrastructure**: GCC 11.4.0 / G++ 11.4.0 (`-O0 -g -fprofile-arcs -ftest-coverage -Wall`)  
**Hardware Environment**: NVIDIA GeForce RTX 4060 (8GB VRAM) on Linux x86_64  

---

## 1. Executive Summary of Root Causes

The audit conducted across 20 representative C and C++ benchmark functions reveals a profound structural dichotomy in the capability of local instruction-tuned code LLMs:

1. **Syntactic and Structural Proficiency (90.0% Compilation Pass Rate)**:
   The model possesses strong grammatical fluency in C99 and modern C++17. In 18 of the 20 functions, the generated code compiled without syntax errors, successfully resolved standard and project headers, created correct test fixtures, and established standard test runners (`int main()` with assertions).

2. **Semantic and Invariant Vulnerability (35.0% Execution Pass Rate)**:
   Despite generating syntactically sound code, **65.0% of the generated test suites failed during runtime execution** (terminating with `SIGABRT` / return code -6).

The root cause of this failure rate is NOT poor code generation; rather, it is the inherent limitation of **autoregressive token prediction operating without a symbolic runtime execution model or ground-truth knowledge retrieval**.

---

## 2. In-Depth Taxonomy Breakdown of Observed Failures

### 2.1 F05: Execution-Path Error & Branch Precedence Masking (Critical)
*Observed in: CPP-01 (`Account::withdraw`), C-09 (`sensor_calibration_lookup`), C-10 (`sensor_fsm_step`)*

#### The Historical C++ Failure Reproduced
In the baseline experiment on `bank::Account::withdraw(long amount)`, the model was instructed to test `WithdrawResult::DAILY_LIMIT_EXCEEDED`. The function under test possesses the following sequential branch hierarchy:
```cpp
WithdrawResult Account::withdraw(long amount) {
    if (amount <= 0) return WithdrawResult::INVALID_AMOUNT;                 // Branch 1
    if (amount > balance_) return WithdrawResult::INSUFFICIENT_FUNDS;       // Branch 2
    if (daily_withdrawn_ + amount > daily_limit_)                           // Branch 3
        return WithdrawResult::DAILY_LIMIT_EXCEEDED;
    ...
}
```
**Observed Model Behavior**:
The model initialized `account(1000, 500)` and executed a sequence of test cases in a single `main()` function:
1. `account.withdraw(400)` -> Succeeded; balance became 600, `daily_withdrawn_` became 400.
2. `account.withdraw(200)` -> Succeeded in triggering `DAILY_LIMIT_EXCEEDED` (`400 + 200 = 600 > 500`).
3. `account.reset_daily_limit()`.
4. `account.withdraw(200)` -> Succeeded; balance became 400.
5. `account.withdraw(100)` -> Succeeded; balance became 300.
6. `account.withdraw(200)` -> Succeeded; balance became 100.
7. Next assertion: `assert(account.withdraw(200) == bank::WithdrawResult::DAILY_LIMIT_EXCEEDED);`

**Root Cause**:
At step 7, the model intended to test `DAILY_LIMIT_EXCEEDED`. However, the account balance had been drained to 100 across the preceding sequential calls. Because Branch 2 (`amount > balance_`, $200 > 100$) precedes Branch 3 (`daily_withdrawn_ + amount > daily_limit_`), the function returned `INSUFFICIENT_FUNDS`. The test assertion aborted immediately.

The model demonstrated **branch precedence blindness**: it selected an input that satisfied the target condition (`amount > daily_limit_`) while failing to satisfy the *precondition* required to reach that branch (`amount <= balance_`).

#### The C-09 Precedence Failure
Similarly, in `sensor_calibration_lookup(float raw, const CalibrationPoint *table, size_t size, float *out)`:
```c
int sensor_calibration_lookup(...) {
    if (table == NULL || calibrated_out == NULL) return SENSOR_ERR_NULL_PTR;  // Check 1
    if (table_size == 0) return SENSOR_ERR_EMPTY_TABLE;                       // Check 2
```
To test empty table handling, the model passed `table = NULL, table_size = 0` and asserted `SENSOR_ERR_EMPTY_TABLE`. Check 1 intercepted the call and returned `SENSOR_ERR_NULL_PTR`, aborting the assertion.

---

### 2.2 F10: State Accumulation and Precondition Invalidation
*Observed in: CPP-01 (`Account::withdraw`), C-05 (`sensor_can_frame_validate`), C-08 (`sensor_circular_buffer_push`)*

#### Root Cause Analysis
LLMs do not maintain a symbolic heap or state-register while generating subsequent test assertions. The model treats each test block in the generated function as an independent semantic concept, but emits them into a **single mutable object context**.

In C-08 (`sensor_circular_buffer_push`):
```c
// Model test code
buf.head = 1;
buf.count = SENSOR_BUF_CAPACITY; // count = 8
assert(sensor_circular_buffer_push(&buf, sample) == SENSOR_OK);
assert(buf.count == SENSOR_BUF_CAPACITY + 1); // Expected 9!
```
The model was told to test "buffer wrapping when head is non-zero". In its attempt to satisfy the prompt, it manually forced `buf.count = 8` and assumed that pushing would increment count to 9 and wrap around. It completely ignored the class invariant that `count >= SENSOR_BUF_CAPACITY` immediately returns `SENSOR_ERR_BUFFER_FULL`.

In C-05 (`sensor_can_frame_validate`):
The model passed `counter = 0, last_counter = 0` expecting `SENSOR_OK`. It failed to realize that alive counters must advance monotonically modulo 16 (`expected = (last + 1) & 0x0F`), meaning `last_counter = 0` requires `counter = 1`.

---

### 2.3 F04: Arithmetic and Cryptographic Hallucination (Expected Outcome Error)
*Observed in: C-02 (`sensor_scale_temperature`), C-06 (`sensor_uart_crc16_verify`), CPP-04 (`calculate_accrued`), CPP-09 (`calculate_fee`)*

#### Root Cause Analysis
Autoregressive language models predict tokens based on statistical co-occurrence, not algebraic execution. When required to assert exact numerical outcomes:

1. **Polynomial Bitwise Calculations (C-06)**:
   The model had to test `sensor_uart_crc16_verify` on payload `{0x01, 0x02, 0x03, 0x04}`. Because a 7B LLM cannot simulate 32 bit-shifts and XOR operations in its weights, it hallucinated an arbitrary plausible-looking hex constant `0x1234` and asserted it as the golden expected CRC.

2. **Floating-Point Arithmetic (C-02 & CPP-04)**:
   - In C-02: For formula `temp = (raw * 0.0805) - 40.0`, at `raw = 4095` the true temperature is $289.65^\circ\text{C}$. The model asserted `fabsf(temp - 0.0f) < EPSILON`, inventing $0.0^\circ\text{C}$ out of thin air.
   - In CPP-04: For simple interest on \$1000 at 5% for 365 days, the true value is \$50.0. The model asserted `result == 500.0`—a 10x arithmetic error.

3. **Percentage and Integer Truncation (CPP-09)**:
   For a 0.5% fee on 100 cents, the integer result is `0` cents. The model asserted `== 0.5 * 100 * 0.005` (evaluating to `0.25` double), conflating integer cents with floating-point dollars and duplicating the percentage fraction.

---

### 2.4 F08 & F09: Hallucinated Mock Interfaces and Redefinitions
*Observed in: CPP-03 (`Account::transfer_to`), CPP-10 (`AuditTrail::verify_integrity`)*

#### Root Cause Analysis
When testing multi-object interactions or complex classes without explicit mock libraries:
- In CPP-03, the model created a derived class `MockAccount : public Account` and marked its methods `override`. Because `Account` methods were declared non-virtual in the header, G++ rejected the code with a compilation error.
- In CPP-10, the model bypassed the real production class `AuditTrail` entirely, defining its own toy functions `compute_hash` and `verify_integrity` inside namespace `bank` in the test file.

---

### 2.5 F03: Missing Include Dependencies
*Observed in: CPP-08 (`CurrencyConverter::convert`)*

#### Root Cause Analysis
The model invoked `std::round` but only included `<cassert>` and `"banking_transactions.hpp"`, omitting `<cmath>`. Under GCC 11 in `-std=c++17`, `<cassert>` does not transitively expose `std::round`.

---

## 3. The Coverage Paradox: Why 100% Branch Coverage != Valid Test Suite

A critical finding from this audit is the **decoupling of test coverage from test validity**:

| Function | Language | Compilation | Execution | Line Cov | Branch Cov | Root Cause of Failure |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `sensor_raw_valid` (C-01) | C | **PASS** | **PASS** | **100.0%** | **100.0%** | None (Baseline benchmark) |
| `Account::withdraw` (CPP-01) | C++ | **PASS** | **FAIL** | **100.0%** | **100.0%** | F05: Balance drained before daily limit check |
| `sensor_scale_temperature` (C-02) | C | **PASS** | **FAIL** | **100.0%** | **100.0%** | F04: Hallucinated expected temperature value |
| `calculate_accrued` (CPP-04) | C++ | **PASS** | **FAIL** | **100.0%** | **100.0%** | F04: 10x order-of-magnitude interest arithmetic error |
| `sensor_circular_buffer_push` (C-08)| C | **PASS** | **FAIL** | **100.0%** | **100.0%** | F10: Buffer full capacity invariant violation |

In all four failed functions above, the test suite achieved **100.0% branch and line coverage before aborting**. 
If an AI platform measures success purely by coverage or compilation, it would falsely mark these broken test suites as high quality. In reality, every single one contained fatal assertion errors that would cause CI/CD pipelines to fail.

---

## 4. Architectural Summary for Future Platform Design

The empirical evidence demonstrates that Qwen2.5-Coder-7B is an exceptional code generation engine that **must not be allowed to act as an unassisted test oracle**. 

Its primary limitations are not linguistic; they are **epistemic**:
1. It does not know the exact runtime state of objects across a test sequence.
2. It cannot evaluate complex formulas or bitwise CRC algorithms.
3. It cannot deduce branch precedence without explicit control-flow guidance.
4. It hallucinates mock signatures when inheritance constraints are absent.

These exact gaps define the non-negotiable retrieval requirements for our future local RAG architecture.

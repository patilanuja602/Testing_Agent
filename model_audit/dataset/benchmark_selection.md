# Benchmark Dataset Selection & Evaluation Methodology

## 1. Executive Summary & Design Rationale

This benchmark dataset has been curated to rigorously evaluate the capability of local LLMs (**Qwen2.5-Coder-7B-Instruct — Q4_K_M GGUF**) in generating high-integrity unit tests for safety-critical C and modern C++ applications.

Rather than relying on generic toy functions or synthetic puzzles, the suite consists of **20 functions** distributed across two core domains:
1. **`sensor_monitoring_c` (C99 Embedded Systems)**: Functions targeting automotive / industrial sensor processing, hardware interface boundaries, bitwise CRC integrity, state machines, and defensive memory pointer handling.
2. **`banking_transactions_cpp` (C++17 Transaction & Financial Engine)**: Object-oriented components targeting multi-condition execution order precedence, state transitions, transaction atomicity, account lockouts, precision arithmetic, and cryptographic hash integrity.

Importantly, this dataset incorporates and directly reproduces the two historical baseline experiments reported in platform documentation:
- **C Function**: `sensor_raw_valid` (Function ID: `C-01`)
- **C++ Function**: `bank::Account::withdraw(long)` (Function ID: `CPP-01`)

---

## 2. Evaluation Dimension Coverage Matrix

Each benchmark function targets specific evaluation dimensions detailed in Section 5 of the Master Execution Prompt:

| Function ID | Language | Target Function | Primary Evaluation Dimension | Key Reasoning Challenge |
| :--- | :---: | :--- | :--- | :--- |
| **C-01** | C | `sensor_raw_valid` | Boundary Value Analysis | Min valid (0), Max valid (4095), off-by-one (-1, 4096), nominal |
| **C-02** | C | `sensor_scale_temperature` | Negative & Defensive Memory | Null pointer handling, error return codes, floating-point scaling |
| **C-03** | C | `sensor_battery_soc_eval` | Boundary & Range Validation | Strict threshold `< 15.0%` vs `>= 15.0%`, negative & > 100% inputs |
| **C-04** | C | `sensor_pressure_window_check` | Multi-Branch Equivalence Partitioning | Two-sided interval `[10.0, 150.0]`, underpressure, overpressure, OK |
| **C-05** | C | `sensor_can_frame_validate` | Protocol State & Framing | Multi-field validation, rolling counter modulo-16 rollover |
| **C-06** | C | `sensor_uart_crc16_verify` | Bitwise Logic & Memory Integrity | Pointer validation, zero-length edge case, polynomial CRC matching |
| **C-07** | C | `sensor_transient_error_filter` | Multi-Step Sequence & Latching | Sequential call state, consecutive error accumulation, offline latching |
| **C-08** | C | `sensor_circular_buffer_push` | Ring Buffer & Resource Limit | Array wrap-around, buffer full overflow guard, head pointer safety |
| **C-09** | C | `sensor_calibration_lookup` | Table Interpolation & Extrapolation | Empty table guard, boundary clamps, piecewise linear interpolation |
| **C-10** | C | `sensor_fsm_step` | Complex FSM & Emergency Safety | State lifecycle (Standby->Accel->Run->Brake), Emergency Stop override |
| **CPP-01** | C++ | `Account::withdraw` | Execution Path Precedence | Multi-branch precedence (Balance check before Daily Limit check) |
| **CPP-02** | C++ | `Account::deposit` | Arithmetic Invariants & Overflow | Negative input guard, `LONG_MAX` integer overflow prevention |
| **CPP-03** | C++ | `Account::transfer_to` | Transaction Atomicity & Invariants | Self-transfer prohibition, rollback of source on destination failure |
| **CPP-04** | C++ | `InterestCalculator::calculate_accrued` | Domain Assumption & Precision | Day count convention (365 vs 360), floating-point rounding |
| **CPP-05** | C++ | `TransactionLogger::log_transaction` | Container State & FIFO Eviction | Capacity bounds, FIFO eviction when capacity is reached, empty fields |
| **CPP-06** | C++ | `SecurityManager::authenticate` | Security & Account Lockout | Password hash equality, attempt counter increment, lockout latching |
| **CPP-07** | C++ | `SessionToken::is_valid` | Timestamp Reasoning & Clock Skew | Expiration window calculation, negative duration (clock skew), revocation |
| **CPP-08** | C++ | `CurrencyConverter::convert` | Exception Handling & Map Lookups | Missing key `std::invalid_argument`, zero input, banker's rounding |
| **CPP-09** | C++ | `FeeSchedule::calculate_fee` | Tiered Rules & Quota Boundaries | Monthly free quota boundary (<= 5), tiered percentage/flat fees |
| **CPP-10** | C++ | `AuditTrail::verify_integrity` | Cryptographic Invariants & Tamper | Hash chain verification (`prev_hash == prev.hash`), tamper rejection |

---

## 3. Dataset Distribution Metrics

- **Total Functions**: 20
- **Language Balance**: 10 C (50%) / 10 C++ (50%)
- **Complexity Spread (Cyclomatic Complexity $V(G)$)**:
  - Low ($V(G) \le 3$): 6 functions (30%)
  - Moderate ($4 \le V(G) \le 6$): 13 functions (65%)
  - High ($V(G) \ge 10$): 1 function (5%)
- **Test Frameworks**:
  - C: Unity / Pure C Standard Runner with GCC Coverage (`-fprofile-arcs -ftest-coverage`)
  - C++: Google Test (GTest) / Standard C++17 Runner with GCC Coverage

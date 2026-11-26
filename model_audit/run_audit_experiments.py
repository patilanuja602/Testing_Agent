#!/usr/bin/env python3
"""
Comprehensive Audit Runner for Qwen2.5-Coder-7B on C and C++ Unit Testing
"""
import os
import sys
import subprocess
import time
import json
import re
import csv
import shutil
from pathlib import Path

BASE_DIR = Path("/home/gitadmin/Documents/Anuja")
AUDIT_DIR = BASE_DIR / "model_audit"
EXPERIMENTS_DIR = AUDIT_DIR / "experiments"
RAW_OUT_DIR = EXPERIMENTS_DIR / "raw_outputs"
GEN_TESTS_DIR = EXPERIMENTS_DIR / "generated_tests"
COMPILER_LOGS_DIR = EXPERIMENTS_DIR / "compiler_logs"
EXEC_LOGS_DIR = EXPERIMENTS_DIR / "execution_logs"
COVERAGE_DIR = EXPERIMENTS_DIR / "coverage"
PERF_DIR = EXPERIMENTS_DIR / "performance"
MUTATION_DIR = EXPERIMENTS_DIR / "mutation"
ANALYSIS_DIR = AUDIT_DIR / "analysis"
REPORTS_DIR = AUDIT_DIR / "reports"

LLAMA_BIN = BASE_DIR / "llama.cpp" / "build-cuda" / "bin" / "llama-completion"
MODEL_PATH = BASE_DIR / "models" / "qwen2.5-coder-7b-instruct-q4_k_m.gguf"

C_PROJECT_DIR = BASE_DIR / "benchmark_projects" / "sensor_monitoring_c"
CPP_PROJECT_DIR = BASE_DIR / "benchmark_projects" / "banking_transactions_cpp"

BENCHMARK_PROMPTS = {
    "C-01": {
        "language": "C",
        "signature": "bool sensor_raw_valid(int raw_adc);",
        "source_file": C_PROJECT_DIR / "src" / "sensor_monitoring.c",
        "include_dir": C_PROJECT_DIR / "include",
        "header_include": '#include "sensor_monitoring.h"',
        "prompt": """Generate comprehensive unit tests in C for the following function from sensor_monitoring.h:

Function signature:
bool sensor_raw_valid(int raw_adc);

Context and Specification:
- Valid raw ADC reading range is [0, 4095] inclusive (SENSOR_RAW_MIN = 0, SENSOR_RAW_MAX = 4095).
- Returns true if 0 <= raw_adc <= 4095.
- Returns false if raw_adc < 0 or raw_adc > 4095.

Requirements for the test file:
- Include "sensor_monitoring.h", <assert.h>, and <stdio.h>.
- Write test assertions covering: minimum valid (0), maximum valid (4095), below minimum (-1, large negative), above maximum (4096, large positive), and normal nominal values.
- Provide an int main() function that executes all assertions and returns 0 on success.
- Return ONLY the executable C code inside a markdown ```c code fence.
"""
    },
    "C-02": {
        "language": "C",
        "signature": "int sensor_scale_temperature(int raw_adc, float *temp_c);",
        "source_file": C_PROJECT_DIR / "src" / "sensor_monitoring.c",
        "include_dir": C_PROJECT_DIR / "include",
        "header_include": '#include "sensor_monitoring.h"',
        "prompt": """Generate comprehensive unit tests in C for the following function from sensor_monitoring.h:

Function signature:
int sensor_scale_temperature(int raw_adc, float *temp_c);

Context and Specification:
- Converts raw ADC to temperature: temp_c = (raw_adc * 0.0805f) - 40.0f.
- Validates raw ADC via sensor_raw_valid(raw_adc) (range [0, 4095]).
- If temp_c == NULL, returns SENSOR_ERR_NULL_PTR (-1).
- If raw_adc is out of range (< 0 or > 4095), writes -999.0f to *temp_c and returns SENSOR_ERR_OUT_OF_RANGE (-2).
- On success, writes scaled float to *temp_c and returns SENSOR_OK (0).

Requirements for the test file:
- Include "sensor_monitoring.h", <assert.h>, <math.h>, and <stdio.h>.
- Test cases: NULL pointer error, out-of-range ADC below 0, out-of-range ADC above 4095, boundary at 0 (result -40.0 C), boundary at 4095, nominal mid-value. Use fabsf for float comparisons with small epsilon.
- Provide an int main() function that runs all tests and returns 0.
- Return ONLY the executable C code inside a markdown ```c code fence.
"""
    },
    "C-03": {
        "language": "C",
        "signature": "int sensor_battery_soc_eval(float soc_percent, bool *low_battery_warning);",
        "source_file": C_PROJECT_DIR / "src" / "sensor_monitoring.c",
        "include_dir": C_PROJECT_DIR / "include",
        "header_include": '#include "sensor_monitoring.h"',
        "prompt": """Generate comprehensive unit tests in C for the following function from sensor_monitoring.h:

Function signature:
int sensor_battery_soc_eval(float soc_percent, bool *low_battery_warning);

Context and Specification:
- Evaluates battery State of Charge percentage in valid range [0.0f, 100.0f].
- If low_battery_warning == NULL, returns SENSOR_ERR_NULL_PTR (-1).
- If soc_percent < 0.0f or soc_percent > 100.0f, returns SENSOR_ERR_OUT_OF_RANGE (-2).
- If soc_percent < 15.0f, sets *low_battery_warning = true and returns SENSOR_OK (0).
- If soc_percent >= 15.0f, sets *low_battery_warning = false and returns SENSOR_OK (0).

Requirements for the test file:
- Include "sensor_monitoring.h", <assert.h>, and <stdio.h>.
- Test cases: NULL pointer, out-of-range negative (-0.1f), out-of-range above 100 (100.1f), boundary exactly 0.0f (warning true), boundary below threshold 14.9f (warning true), boundary at threshold 15.0f (warning false), boundary above threshold 15.1f (warning false), upper bound 100.0f (warning false).
- Provide an int main() function that runs all tests and returns 0.
- Return ONLY the executable C code inside a markdown ```c code fence.
"""
    },
    "C-04": {
        "language": "C",
        "signature": "PressureStatus sensor_pressure_window_check(float pressure_bar);",
        "source_file": C_PROJECT_DIR / "src" / "sensor_monitoring.c",
        "include_dir": C_PROJECT_DIR / "include",
        "header_include": '#include "sensor_monitoring.h"',
        "prompt": """Generate comprehensive unit tests in C for the following function from sensor_monitoring.h:

Enum and Function signature:
typedef enum {
    PRESSURE_OK = 0,
    PRESSURE_FAULT_UNDERPRESSURE = 1,
    PRESSURE_FAULT_OVERPRESSURE = 2
} PressureStatus;

PressureStatus sensor_pressure_window_check(float pressure_bar);

Context and Specification:
- Safe operating pressure window is [10.0f, 150.0f] bar inclusive.
- If pressure_bar < 10.0f, returns PRESSURE_FAULT_UNDERPRESSURE.
- If pressure_bar > 150.0f, returns PRESSURE_FAULT_OVERPRESSURE.
- If 10.0f <= pressure_bar <= 150.0f, returns PRESSURE_OK.

Requirements for the test file:
- Include "sensor_monitoring.h", <assert.h>, and <stdio.h>.
- Test cases: underpressure (< 10.0f, e.g. 9.9f, 0.0f, -5.0f), lower boundary (10.0f -> PRESSURE_OK), nominal mid-point (50.0f -> PRESSURE_OK), upper boundary (150.0f -> PRESSURE_OK), overpressure (> 150.0f, e.g. 150.1f, 200.0f).
- Provide an int main() function that executes all assertions and returns 0.
- Return ONLY the executable C code inside a markdown ```c code fence.
"""
    },
    "C-05": {
        "language": "C",
        "signature": "int sensor_can_frame_validate(uint16_t id, uint8_t dlc, uint8_t counter, uint8_t last_counter);",
        "source_file": C_PROJECT_DIR / "src" / "sensor_monitoring.c",
        "include_dir": C_PROJECT_DIR / "include",
        "header_include": '#include "sensor_monitoring.h"',
        "prompt": """Generate comprehensive unit tests in C for the following function from sensor_monitoring.h:

Function signature:
int sensor_can_frame_validate(uint16_t id, uint8_t dlc, uint8_t counter, uint8_t last_counter);

Context and Specification:
- Valid CAN IDs are in range [0x2F0, 0x2F7] inclusive. Returns SENSOR_ERR_OUT_OF_RANGE (-2) if id < 0x2F0 or id > 0x2F7.
- DLC must be exactly 8. Returns SENSOR_ERR_INVALID_DLC (-3) if dlc != 8.
- The alive counter must advance modulo 16: expected = (last_counter + 1) & 0x0F. Returns SENSOR_ERR_COUNTER_SEQUENCE (-4) if counter != expected.
- On success, returns SENSOR_OK (0).

Requirements for the test file:
- Include "sensor_monitoring.h", <assert.h>, <stdint.h>, and <stdio.h>.
- Test cases: Invalid ID below 0x2F0 (e.g. 0x2EF), invalid ID above 0x2F7 (e.g. 0x2F8), boundary valid IDs (0x2F0, 0x2F7), invalid DLC (e.g. 7, 9), valid DLC (8), valid sequential counter (last=0, curr=1), counter modulo-16 wrap-around (last=15, curr=0), out-of-order counter sequence (last=2, curr=4).
- Provide an int main() function that executes all assertions and returns 0.
- Return ONLY the executable C code inside a markdown ```c code fence.
"""
    },
    "C-06": {
        "language": "C",
        "signature": "int sensor_uart_crc16_verify(const uint8_t *payload, uint8_t len, uint16_t expected_crc);",
        "source_file": C_PROJECT_DIR / "src" / "sensor_monitoring.c",
        "include_dir": C_PROJECT_DIR / "include",
        "header_include": '#include "sensor_monitoring.h"',
        "prompt": """Generate comprehensive unit tests in C for the following function from sensor_monitoring.h:

Function signature:
int sensor_uart_crc16_verify(const uint8_t *payload, uint8_t len, uint16_t expected_crc);

Context and Specification:
- Computes CRC-16-CCITT (polynomial 0x1021, initial value 0xFFFF) over payload of length len.
- If payload == NULL, returns SENSOR_ERR_NULL_PTR (-1).
- If len == 0, returns SENSOR_ERR_OUT_OF_RANGE (-2).
- If computed CRC != expected_crc, returns SENSOR_ERR_CRC_MISMATCH (-5).
- If CRC matches expected_crc, returns SENSOR_OK (0).

Requirements for the test file:
- Include "sensor_monitoring.h", <assert.h>, <stdint.h>, and <stdio.h>.
- Test cases: NULL payload pointer, zero length, corrupted/mismatched CRC, and a valid payload with matching CRC (for example payload = {0x01, 0x02, 0x03, 0x04}). You can compute or calculate the matching CRC or test CRC mismatch first.
- Provide an int main() function executing all assertions and returning 0.
- Return ONLY the executable C code inside a markdown ```c code fence.
"""
    },
    "C-07": {
        "language": "C",
        "signature": "int sensor_transient_error_filter(int error_occurred, int *consecutive_errors, int *status_offline);",
        "source_file": C_PROJECT_DIR / "src" / "sensor_monitoring.c",
        "include_dir": C_PROJECT_DIR / "include",
        "header_include": '#include "sensor_monitoring.h"',
        "prompt": """Generate comprehensive unit tests in C for the following function from sensor_monitoring.h:

Function signature:
int sensor_transient_error_filter(int error_occurred, int *consecutive_errors, int *status_offline);

Context and Specification:
- If consecutive_errors == NULL or status_offline == NULL, returns SENSOR_ERR_NULL_PTR (-1).
- If error_occurred != 0: increments (*consecutive_errors)++. If *consecutive_errors >= 3, sets *status_offline = 1.
- If error_occurred == 0: resets *consecutive_errors = 0 (status_offline is NOT cleared back to 0; it stays latched).
- Returns SENSOR_OK (0).

Requirements for the test file:
- Include "sensor_monitoring.h", <assert.h>, and <stdio.h>.
- Test cases: NULL consecutive_errors pointer, NULL status_offline pointer, single transient error (counter becomes 1, offline remains 0), recovery on error=0 (counter resets to 0, offline remains 0), 3 consecutive errors triggering offline latch (*consecutive_errors=3, *status_offline=1), fourth consecutive error (*consecutive_errors=4, *status_offline=1).
- Provide an int main() function executing all assertions and returning 0.
- Return ONLY the executable C code inside a markdown ```c code fence.
"""
    },
    "C-08": {
        "language": "C",
        "signature": "int sensor_circular_buffer_push(SensorCircularBuffer *buf, uint32_t sample);",
        "source_file": C_PROJECT_DIR / "src" / "sensor_monitoring.c",
        "include_dir": C_PROJECT_DIR / "include",
        "header_include": '#include "sensor_monitoring.h"',
        "prompt": """Generate comprehensive unit tests in C for the following function from sensor_monitoring.h:

Types and Function signature:
#define SENSOR_BUF_CAPACITY 8
typedef struct {
    uint32_t data[SENSOR_BUF_CAPACITY];
    size_t head;
    size_t count;
} SensorCircularBuffer;

int sensor_circular_buffer_push(SensorCircularBuffer *buf, uint32_t sample);

Context and Specification:
- If buf == NULL, returns SENSOR_ERR_NULL_PTR (-1).
- If buf->count >= SENSOR_BUF_CAPACITY (8), returns SENSOR_ERR_BUFFER_FULL (-6).
- Otherwise writes sample at (buf->head + buf->count) % SENSOR_BUF_CAPACITY, increments buf->count, and returns SENSOR_OK (0).

Requirements for the test file:
- Include "sensor_monitoring.h", <assert.h>, <stdint.h>, and <stdio.h>.
- Test cases: NULL buffer pointer, pushing into empty buffer (count becomes 1, sample stored), filling buffer to capacity (count becomes 8), pushing when buffer is full (returns SENSOR_ERR_BUFFER_FULL, count remains 8), wrapping when head is non-zero.
- Provide an int main() function executing all assertions and returning 0.
- Return ONLY the executable C code inside a markdown ```c code fence.
"""
    },
    "C-09": {
        "language": "C",
        "signature": "int sensor_calibration_lookup(float raw_val, const CalibrationPoint *table, size_t table_size, float *calibrated_out);",
        "source_file": C_PROJECT_DIR / "src" / "sensor_monitoring.c",
        "include_dir": C_PROJECT_DIR / "include",
        "header_include": '#include "sensor_monitoring.h"',
        "prompt": """Generate comprehensive unit tests in C for the following function from sensor_monitoring.h:

Types and Function signature:
typedef struct {
    float raw;
    float calibrated;
} CalibrationPoint;

int sensor_calibration_lookup(float raw_val, const CalibrationPoint *table, size_t table_size, float *calibrated_out);

Context and Specification:
- Performs linear interpolation from a sorted calibration table.
- If table == NULL or calibrated_out == NULL, returns SENSOR_ERR_NULL_PTR (-1).
- If table_size == 0, returns SENSOR_ERR_EMPTY_TABLE (-7).
- If raw_val <= table[0].raw, returns table[0].calibrated and SENSOR_OK (0).
- If raw_val >= table[table_size - 1].raw, returns table[table_size - 1].calibrated and SENSOR_OK (0).
- If raw_val is between table[i].raw and table[i+1].raw, performs linear interpolation:
  calibrated = table[i].calibrated + ((raw_val - table[i].raw) / (table[i+1].raw - table[i].raw)) * (table[i+1].calibrated - table[i].calibrated)
  and returns SENSOR_OK (0).

Requirements for the test file:
- Include "sensor_monitoring.h", <assert.h>, <math.h>, and <stdio.h>.
- Test cases: NULL table pointer, NULL output pointer, empty table (size 0), clamping at/below lower bound, clamping at/above upper bound, exact point match on table entry, interpolation between points (e.g. midway).
- Provide an int main() function executing all assertions and returning 0.
- Return ONLY the executable C code inside a markdown ```c code fence.
"""
    },
    "C-10": {
        "language": "C",
        "signature": "ConveyorState sensor_fsm_step(ConveyorState current_state, MotorCommand cmd, float current_rpm, float target_rpm, bool hardware_fault);",
        "source_file": C_PROJECT_DIR / "src" / "sensor_monitoring.c",
        "include_dir": C_PROJECT_DIR / "include",
        "header_include": '#include "sensor_monitoring.h"',
        "prompt": """Generate comprehensive unit tests in C for the following function from sensor_monitoring.h:

Types and Function signature:
typedef enum {
    FSM_STANDBY = 0,
    FSM_ACCELERATING = 1,
    FSM_RUNNING = 2,
    FSM_BRAKING = 3,
    FSM_FAULT_LATCHED = 4
} ConveyorState;

typedef enum {
    CMD_NONE = 0,
    CMD_START = 1,
    CMD_STOP = 2,
    CMD_EMERGENCY_STOP = 3,
    CMD_RESET = 4
} MotorCommand;

ConveyorState sensor_fsm_step(ConveyorState current_state, MotorCommand cmd, float current_rpm, float target_rpm, bool hardware_fault);

Context and Specification:
- If hardware_fault is true or cmd == CMD_EMERGENCY_STOP, returns FSM_FAULT_LATCHED from ANY state.
- In FSM_STANDBY: if cmd == CMD_START, transitions to FSM_ACCELERATING.
- In FSM_ACCELERATING: if current_rpm >= target_rpm && target_rpm > 0.0f, transitions to FSM_RUNNING. If cmd == CMD_STOP, transitions to FSM_BRAKING.
- In FSM_RUNNING: if cmd == CMD_STOP, transitions to FSM_BRAKING.
- In FSM_BRAKING: if current_rpm <= 0.0f, transitions to FSM_STANDBY.
- In FSM_FAULT_LATCHED: if cmd == CMD_RESET && !hardware_fault, transitions to FSM_STANDBY; otherwise remains FSM_FAULT_LATCHED.
- Otherwise returns current_state.

Requirements for the test file:
- Include "sensor_monitoring.h", <assert.h>, and <stdio.h>.
- Test cases: emergency stop from running, hardware fault override from standby, normal lifecycle (STANDBY -> START -> ACCELERATING -> target reached -> RUNNING -> STOP -> BRAKING -> stopped -> STANDBY), fault recovery (FAULT_LATCHED + CMD_RESET without fault -> STANDBY), fault recovery blocked if hardware_fault still true.
- Provide an int main() function executing all assertions and returning 0.
- Return ONLY the executable C code inside a markdown ```c code fence.
"""
    },
    "CPP-01": {
        "language": "C++",
        "signature": "WithdrawResult Account::withdraw(long amount);",
        "source_file": CPP_PROJECT_DIR / "src" / "banking_transactions.cpp",
        "include_dir": CPP_PROJECT_DIR / "include",
        "header_include": '#include "banking_transactions.hpp"',
        "prompt": """Generate comprehensive unit tests in C++ for the following member function from banking_transactions.hpp:

Class declaration:
namespace bank {

enum class WithdrawResult {
    SUCCESS = 0,
    INVALID_AMOUNT,
    INSUFFICIENT_FUNDS,
    DAILY_LIMIT_EXCEEDED
};

class Account {
public:
    Account(long initial_balance, long daily_limit);
    WithdrawResult withdraw(long amount);
    long get_balance() const;
    long get_daily_withdrawn() const;
    long get_daily_limit() const;
    void reset_daily_limit();
};

}

Requirements:
1. If amount <= 0, returns WithdrawResult::INVALID_AMOUNT.
2. If amount > balance, returns WithdrawResult::INSUFFICIENT_FUNDS.
3. If daily_withdrawn + amount > daily_limit, returns WithdrawResult::DAILY_LIMIT_EXCEEDED.
4. Otherwise deducts amount from balance, adds amount to daily_withdrawn, and returns WithdrawResult::SUCCESS.

Write a complete, self-contained standalone C++ test file that includes "banking_transactions.hpp" and <cassert>, tests all branches and state updates, and defines an int main() that runs all tests and returns 0 on success.
Output ONLY the C++ code block.
"""
    },
    "CPP-02": {
        "language": "C++",
        "signature": "DepositResult Account::deposit(long amount);",
        "source_file": CPP_PROJECT_DIR / "src" / "banking_transactions.cpp",
        "include_dir": CPP_PROJECT_DIR / "include",
        "header_include": '#include "banking_transactions.hpp"',
        "prompt": """Generate comprehensive unit tests in C++ for the following member function from banking_transactions.hpp:

Class declaration:
namespace bank {

enum class DepositResult {
    SUCCESS = 0,
    INVALID_AMOUNT,
    OVERFLOW_ERROR
};

class Account {
public:
    Account(long initial_balance, long daily_limit);
    DepositResult deposit(long amount);
    long get_balance() const;
};

}

Requirements:
1. If amount <= 0, returns DepositResult::INVALID_AMOUNT.
2. If LONG_MAX - amount < balance, returns DepositResult::OVERFLOW_ERROR (guards against integer overflow).
3. Otherwise adds amount to balance and returns DepositResult::SUCCESS.

Write a complete, self-contained standalone C++ test file that includes "banking_transactions.hpp", <climits>, and <cassert>, tests invalid amounts (0, negative), normal positive deposit, balance update, and overflow condition near LONG_MAX.
Define an int main() that runs all tests and returns 0 on success.
Output ONLY the C++ code block.
"""
    },
    "CPP-03": {
        "language": "C++",
        "signature": "TransferResult Account::transfer_to(Account &destination, long amount);",
        "source_file": CPP_PROJECT_DIR / "src" / "banking_transactions.cpp",
        "include_dir": CPP_PROJECT_DIR / "include",
        "header_include": '#include "banking_transactions.hpp"',
        "prompt": """Generate comprehensive unit tests in C++ for the following member function from banking_transactions.hpp:

Class declaration:
namespace bank {

enum class TransferResult {
    SUCCESS = 0,
    SELF_TRANSFER_PROHIBITED,
    SOURCE_WITHDRAW_FAILED,
    DESTINATION_CREDIT_FAILED
};

class Account {
public:
    Account(long initial_balance, long daily_limit);
    TransferResult transfer_to(Account &destination, long amount);
    long get_balance() const;
};

}

Requirements:
1. If this == &destination, returns TransferResult::SELF_TRANSFER_PROHIBITED.
2. If withdraw(amount) on source account fails, returns TransferResult::SOURCE_WITHDRAW_FAILED.
3. If destination.deposit(amount) fails, the withdrawal is rolled back (deposit back into source) and returns TransferResult::DESTINATION_CREDIT_FAILED.
4. On success, transfers amount between accounts and returns TransferResult::SUCCESS.

Write a complete, self-contained standalone C++ test file that includes "banking_transactions.hpp" and <cassert>, tests self-transfer attempt, insufficient funds transfer failure, successful transfer, and balance updates for both accounts.
Define an int main() that runs all tests and returns 0 on success.
Output ONLY the C++ code block.
"""
    },
    "CPP-04": {
        "language": "C++",
        "signature": "double InterestCalculator::calculate_accrued(double principal, double annual_rate, int days);",
        "source_file": CPP_PROJECT_DIR / "src" / "banking_transactions.cpp",
        "include_dir": CPP_PROJECT_DIR / "include",
        "header_include": '#include "banking_transactions.hpp"',
        "prompt": """Generate comprehensive unit tests in C++ for the following static member function from banking_transactions.hpp:

Class declaration:
namespace bank {

class InterestCalculator {
public:
    static double calculate_accrued(double principal, double annual_rate, int days);
};

}

Requirements:
1. If principal < 0.0 or annual_rate < 0.0 or days < 0, returns -1.0.
2. Otherwise calculates accrued simple daily interest using the 365-day convention:
   accrued = principal * (annual_rate / 365.0) * static_cast<double>(days).

Write a complete, self-contained standalone C++ test file that includes "banking_transactions.hpp", <cmath>, and <cassert>, tests negative principal, negative rate, negative days, zero days, zero principal, and normal interest calculation with floating point tolerance.
Define an int main() that runs all tests and returns 0 on success.
Output ONLY the C++ code block.
"""
    },
    "CPP-05": {
        "language": "C++",
        "signature": "bool TransactionLogger::log_transaction(const Transaction &tx);",
        "source_file": CPP_PROJECT_DIR / "src" / "banking_transactions.cpp",
        "include_dir": CPP_PROJECT_DIR / "include",
        "header_include": '#include "banking_transactions.hpp"',
        "prompt": """Generate comprehensive unit tests in C++ for the following member function from banking_transactions.hpp:

Class declaration:
namespace bank {

struct Transaction {
    std::string tx_id;
    long amount;
    std::string timestamp;
    std::string type;
};

class TransactionLogger {
public:
    explicit TransactionLogger(size_t max_capacity = 100);
    bool log_transaction(const Transaction &tx);
    size_t count() const;
    void clear();
};

}

Requirements:
1. If tx.tx_id.empty() or tx.amount == 0, returns false (transaction rejected).
2. If count() reaches max_capacity, the oldest transaction is evicted before logging the new transaction.
3. Appends transaction and returns true.

Write a complete, self-contained standalone C++ test file that includes "banking_transactions.hpp" and <cassert>, tests empty tx_id, zero amount, valid logging, count verification, capacity eviction behavior (e.g. logger with capacity 2), and clear().
Define an int main() that runs all tests and returns 0 on success.
Output ONLY the C++ code block.
"""
    },
    "CPP-06": {
        "language": "C++",
        "signature": "AuthStatus SecurityManager::authenticate(const std::string &username, const std::string &provided_hash, const std::string &stored_hash, int current_attempts);",
        "source_file": CPP_PROJECT_DIR / "src" / "banking_transactions.cpp",
        "include_dir": CPP_PROJECT_DIR / "include",
        "header_include": '#include "banking_transactions.hpp"',
        "prompt": """Generate comprehensive unit tests in C++ for the following static member function from banking_transactions.hpp:

Class declaration:
namespace bank {

enum class AuthStatus {
    AUTHENTICATED = 0,
    INVALID_CREDENTIALS,
    ACCOUNT_LOCKED,
    INVALID_INPUT
};

class SecurityManager {
public:
    static const int MAX_ATTEMPTS = 3;
    static AuthStatus authenticate(const std::string &username,
                                   const std::string &provided_hash,
                                   const std::string &stored_hash,
                                   int current_attempts);
};

}

Requirements:
1. If username.empty() or provided_hash.empty(), returns AuthStatus::INVALID_INPUT.
2. If current_attempts >= MAX_ATTEMPTS (3), returns AuthStatus::ACCOUNT_LOCKED.
3. If provided_hash == stored_hash, returns AuthStatus::AUTHENTICATED.
4. Otherwise returns AuthStatus::INVALID_CREDENTIALS.

Write a complete, self-contained standalone C++ test file that includes "banking_transactions.hpp" and <cassert>, tests empty username, empty hash, locked account (attempts >= 3), successful authentication, and invalid credentials.
Define an int main() that runs all tests and returns 0 on success.
Output ONLY the C++ code block.
"""
    },
    "CPP-07": {
        "language": "C++",
        "signature": "bool SessionToken::is_valid(uint64_t current_timestamp) const;",
        "source_file": CPP_PROJECT_DIR / "src" / "banking_transactions.cpp",
        "include_dir": CPP_PROJECT_DIR / "include",
        "header_include": '#include "banking_transactions.hpp"',
        "prompt": """Generate comprehensive unit tests in C++ for the following member function from banking_transactions.hpp:

Class declaration:
namespace bank {

class SessionToken {
public:
    SessionToken(uint64_t issued_at, uint64_t timeout_seconds);
    bool is_valid(uint64_t current_timestamp) const;
    void revoke();
    bool is_revoked() const;
};

}

Requirements:
1. If token is revoked (is_revoked() is true), returns false.
2. If current_timestamp < issued_at (clock skew / backwards time), returns false.
3. If (current_timestamp - issued_at) <= timeout_seconds, returns true; if elapsed > timeout_seconds, returns false.

Write a complete, self-contained standalone C++ test file that includes "banking_transactions.hpp" and <cassert>, tests active token within timeout, token exactly at timeout boundary, expired token, clock skew timestamp, and token revocation.
Define an int main() that runs all tests and returns 0 on success.
Output ONLY the C++ code block.
"""
    },
    "CPP-08": {
        "language": "C++",
        "signature": "long CurrencyConverter::convert(long amount_cents, const std::string &from_curr, const std::string &to_curr) const;",
        "source_file": CPP_PROJECT_DIR / "src" / "banking_transactions.cpp",
        "include_dir": CPP_PROJECT_DIR / "include",
        "header_include": '#include "banking_transactions.hpp"',
        "prompt": """Generate comprehensive unit tests in C++ for the following member function from banking_transactions.hpp:

Class declaration:
namespace bank {

class CurrencyConverter {
public:
    CurrencyConverter();
    void set_rate(const std::string &from_curr, const std::string &to_curr, double rate);
    long convert(long amount_cents, const std::string &from_curr, const std::string &to_curr) const;
};

}

Requirements:
1. If amount_cents <= 0, returns 0.
2. If from_curr == to_curr, returns amount_cents.
3. If currency pair is unknown/missing in rates table, throws std::invalid_argument exception.
4. Otherwise returns static_cast<long>(std::round(amount_cents * rate)).
Note: Default constructor initializes "USD_EUR" (0.92), "EUR_USD" (1.087), "USD_GBP" (0.79), "GBP_USD" (1.265).

Write a complete, self-contained standalone C++ test file that includes "banking_transactions.hpp", <stdexcept>, and <cassert>, tests zero/negative amount, identical currencies, standard conversion (e.g. USD to EUR), and exception throwing for unsupported currency pair.
Define an int main() that runs all tests and returns 0 on success.
Output ONLY the C++ code block.
"""
    },
    "CPP-09": {
        "language": "C++",
        "signature": "long FeeSchedule::calculate_fee(long amount_cents, AccountType type, int monthly_tx_count);",
        "source_file": CPP_PROJECT_DIR / "src" / "banking_transactions.cpp",
        "include_dir": CPP_PROJECT_DIR / "include",
        "header_include": '#include "banking_transactions.hpp"',
        "prompt": """Generate comprehensive unit tests in C++ for the following static member function from banking_transactions.hpp:

Class declaration:
namespace bank {

enum class AccountType {
    STANDARD = 0,
    PREMIUM,
    STUDENT,
    BUSINESS
};

class FeeSchedule {
public:
    static long calculate_fee(long amount_cents, AccountType type, int monthly_tx_count);
};

}

Requirements:
1. If amount_cents <= 0, returns 0.
2. If monthly_tx_count <= 5, returns 0 (first 5 transactions per month are free).
3. If monthly_tx_count > 5:
   - AccountType::PREMIUM: flat fee of 10 cents.
   - AccountType::STUDENT: flat fee of 5 cents.
   - AccountType::BUSINESS: 0.5% (amount_cents * 0.005).
   - AccountType::STANDARD: 1.0% (amount_cents * 0.01).

Write a complete, self-contained standalone C++ test file that includes "banking_transactions.hpp" and <cassert>, tests free tier transactions (count <= 5), zero amount, and fees for PREMIUM, STUDENT, BUSINESS, and STANDARD accounts when count > 5.
Define an int main() that runs all tests and returns 0 on success.
Output ONLY the C++ code block.
"""
    },
    "CPP-10": {
        "language": "C++",
        "signature": "bool AuditTrail::verify_integrity(const std::vector<TransactionRecord> &records);",
        "source_file": CPP_PROJECT_DIR / "src" / "banking_transactions.cpp",
        "include_dir": CPP_PROJECT_DIR / "include",
        "header_include": '#include "banking_transactions.hpp"',
        "prompt": """Generate comprehensive unit tests in C++ for the following static member function from banking_transactions.hpp:

Types and Class declaration:
namespace bank {

struct TransactionRecord {
    std::string tx_id;
    long amount;
    uint32_t prev_hash;
    uint32_t hash;
};

class AuditTrail {
public:
    static uint32_t compute_hash(const std::string &tx_id, long amount, uint32_t prev_hash);
    static bool verify_integrity(const std::vector<TransactionRecord> &records);
};

}

Requirements:
1. If records.empty(), returns true.
2. For the first record, prev_hash must be 0.
3. For each record, compute_hash(rec.tx_id, rec.amount, rec.prev_hash) must equal rec.hash.
4. For each subsequent record, rec.prev_hash must match the preceding record's hash.
5. Returns true if all records are valid; returns false if any hash or link is tampered/broken.

Write a complete, self-contained standalone C++ test file that includes "banking_transactions.hpp" and <cassert>, tests empty records vector, a valid 2-record chain using AuditTrail::compute_hash, broken prev_hash link, and tampered transaction data.
Define an int main() that runs all tests and returns 0 on success.
Output ONLY the C++ code block.
"""
    }
}

def clean_code(raw_text, lang):
    """Extract code block from markdown or return raw text if no block"""
    match = re.search(r"```(?:c|cpp|c\+\+)?\s*\n(.*?)```", raw_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return raw_text.strip()

def run_single_inference(func_id, prompt_data, seed=42, temp=0.2):
    prompt_file = f"/tmp/prompt_{func_id}_{seed}.txt"
    formatted = f"<|im_start|>system\nYou are an expert C and C++ unit-testing engineer. Write high-quality, comprehensive standalone unit tests using standard assert statements. Return ONLY complete C or C++ code inside markdown code fences with an int main() function executing all assertions.<|im_end|>\n<|im_start|>user\n{prompt_data['prompt']}<|im_end|>\n<|im_start|>assistant\n"
    with open(prompt_file, "w") as f:
        f.write(formatted)
    
    cmd = [
        str(LLAMA_BIN),
        "-m", str(MODEL_PATH),
        "-ngl", "28",
        "-c", "4096",
        "-n", "1536",
        "--temp", str(temp),
        "--seed", str(seed),
        "-f", prompt_file,
        "--no-display-prompt",
        "-no-cnv",
        "--simple-io",
        "--no-warmup"
    ]
    
    t0 = time.time()
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    t1 = time.time()
    
    # parse performance metrics
    perf = {
        "func_id": func_id,
        "seed": seed,
        "temperature": temp,
        "wall_time_sec": t1 - t0,
        "prompt_eval_ms": None,
        "prompt_eval_tokens": None,
        "prompt_eval_speed_ts": None,
        "eval_ms": None,
        "eval_tokens": None,
        "eval_speed_ts": None
    }
    for line in res.stderr.splitlines():
        if "prompt eval time" in line:
            m = re.search(r"=\s*([0-9.]+)\s*ms\s*/\s*([0-9]+)\s*tokens\s*\(\s*([0-9.]+)\s*ms per token,\s*([0-9.]+)\s*tokens per second", line)
            if m:
                perf["prompt_eval_ms"] = float(m.group(1))
                perf["prompt_eval_tokens"] = int(m.group(2))
                perf["prompt_eval_speed_ts"] = float(m.group(4))
        if "eval time" in line and "prompt eval" not in line:
            m = re.search(r"=\s*([0-9.]+)\s*ms\s*/\s*([0-9]+)\s*runs\s*\(\s*([0-9.]+)\s*ms per token,\s*([0-9.]+)\s*tokens per second", line)
            if m:
                perf["eval_ms"] = float(m.group(1))
                perf["eval_tokens"] = int(m.group(2))
                perf["eval_speed_ts"] = float(m.group(4))
                
    return res.stdout, res.stderr, perf

def compile_and_test(func_id, prompt_data, code_text):
    lang = prompt_data["language"]
    ext = "c" if lang == "C" else "cpp"
    test_file = GEN_TESTS_DIR / f"test_{func_id}.{ext}"
    bin_file = Path(f"/tmp/bin_test_{func_id}")
    
    with open(test_file, "w") as f:
        f.write(code_text)
        
    # Clean previous gcov files in source dir
    src_dir = prompt_data["source_file"].parent
    for gc_file in src_dir.glob("*.gc*"):
        try: gc_file.unlink()
        except: pass
        
    # Build command
    if lang == "C":
        cmd_compile = [
            "gcc", "-O0", "-g",
            "-fprofile-arcs", "-ftest-coverage",
            f"-I{prompt_data['include_dir']}",
            str(test_file),
            str(prompt_data["source_file"]),
            "-o", str(bin_file),
            "-lm"
        ]
    else:
        cmd_compile = [
            "g++", "-std=c++17", "-O0", "-g",
            "-fprofile-arcs", "-ftest-coverage",
            f"-I{prompt_data['include_dir']}",
            str(test_file),
            str(prompt_data["source_file"]),
            "-o", str(bin_file)
        ]
        
    res_comp = subprocess.run(cmd_compile, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    compile_log = COMPILER_LOGS_DIR / f"{func_id}_compile.log"
    with open(compile_log, "w") as f:
        f.write(f"Command: {' '.join(cmd_compile)}\nReturn code: {res_comp.returncode}\n")
        f.write("=== STDOUT ===\n" + res_comp.stdout + "\n")
        f.write("=== STDERR ===\n" + res_comp.stderr + "\n")
        
    compile_success = (res_comp.returncode == 0)
    exec_success = False
    exec_rc = -1
    exec_out = ""
    exec_err = ""
    line_cov = 0.0
    branch_cov = 0.0
    
    if compile_success:
        try:
            res_exec = subprocess.run([str(bin_file)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            exec_rc = res_exec.returncode
            exec_out = res_exec.stdout
            exec_err = res_exec.stderr
            exec_success = (res_exec.returncode == 0)
        except subprocess.TimeoutExpired:
            exec_rc = -999
            exec_err = "Execution timed out (5s)"
        except Exception as e:
            exec_rc = -998
            exec_err = str(e)
            
        exec_log = EXEC_LOGS_DIR / f"{func_id}_exec.log"
        with open(exec_log, "w") as f:
            f.write(f"Binary: {bin_file}\nReturn code: {exec_rc}\n")
            f.write("=== STDOUT ===\n" + exec_out + "\n")
            f.write("=== STDERR ===\n" + exec_err + "\n")
            
        # Run gcov
        cmd_gcov = ["gcov", "-b", "-c", str(prompt_data["source_file"])]
        res_gcov = subprocess.run(cmd_gcov, cwd=str(src_dir), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        cov_log = COVERAGE_DIR / f"{func_id}_gcov.txt"
        with open(cov_log, "w") as f:
            f.write(res_gcov.stdout + "\n" + res_gcov.stderr)
            
        # Parse gcov output for the source file
        src_name = prompt_data["source_file"].name
        lines = res_gcov.stdout.splitlines()
        found_file = False
        for i, l in enumerate(lines):
            if f"File '{src_name}'" in l or f"File '{prompt_data['source_file']}'" in l:
                found_file = True
            if found_file and "Lines executed:" in l:
                m = re.search(r"Lines executed:([0-9.]+)%", l)
                if m: line_cov = float(m.group(1))
            if found_file and "Branches executed:" in l:
                m = re.search(r"Branches executed:([0-9.]+)%", l)
                if m: branch_cov = float(m.group(1))
                break
                
    return {
        "compile_success": compile_success,
        "compile_rc": res_comp.returncode,
        "compile_err": res_comp.stderr,
        "exec_success": exec_success,
        "exec_rc": exec_rc,
        "exec_out": exec_out,
        "exec_err": exec_err,
        "line_coverage": line_cov,
        "branch_coverage": branch_cov
    }

def main():
    print("=" * 60)
    print("STARTING COMPLETE AUDIT RUNNER ON QWEN2.5-CODER-7B")
    print("=" * 60)
    
    # Ensure dirs exist
    for d in [RAW_OUT_DIR, GEN_TESTS_DIR, COMPILER_LOGS_DIR, EXEC_LOGS_DIR, COVERAGE_DIR, PERF_DIR, MUTATION_DIR, ANALYSIS_DIR, REPORTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
        
    audit_results = []
    
    # 1. Main benchmark evaluation (20 functions)
    for func_id, prompt_data in BENCHMARK_PROMPTS.items():
        print(f"\nEvaluating {func_id} ({prompt_data['signature']})...")
        raw_out, stderr, perf = run_single_inference(func_id, prompt_data, seed=42, temp=0.2)
        
        # Save raw output
        with open(RAW_OUT_DIR / f"{func_id}_raw.txt", "w") as f:
            f.write(raw_out)
        with open(PERF_DIR / f"{func_id}_perf.json", "w") as f:
            json.dump(perf, f, indent=2)
            
        clean_t = clean_code(raw_out, prompt_data["language"])
        test_res = compile_and_test(func_id, prompt_data, clean_t)
        
        row = {
            "func_id": func_id,
            "language": prompt_data["language"],
            "signature": prompt_data["signature"],
            "compile_success": test_res["compile_success"],
            "exec_success": test_res["exec_success"],
            "exec_rc": test_res["exec_rc"],
            "line_coverage": test_res["line_coverage"],
            "branch_coverage": test_res["branch_coverage"],
            "eval_speed_ts": perf["eval_speed_ts"],
            "wall_time_sec": perf["wall_time_sec"]
        }
        audit_results.append(row)
        print(f"  Compile: {'PASS' if test_res['compile_success'] else 'FAIL'}, Exec: {'PASS' if test_res['exec_success'] else 'FAIL (rc=' + str(test_res['exec_rc']) + ')'}, Lines: {test_res['line_coverage']}%, Branches: {test_res['branch_coverage']}%, Speed: {perf['eval_speed_ts']} t/s")
        
    # Write summary CSV
    with open(ANALYSIS_DIR / "audit_summary_20.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(audit_results[0].keys()))
        writer.writeheader()
        writer.writerows(audit_results)
        
    print("\nBenchmark generation completed.")

if __name__ == "__main__":
    main()

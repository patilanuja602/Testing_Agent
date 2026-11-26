# Concrete Recommendations for Future Local RAG Architecture
## Derived from Empirical GPU Audit of Qwen2.5-Coder-7B

**Document Version**: 1.0.0  
**Context**: Blueprint for the subsequent RAG implementation phase of our AI-assisted C/C++ Unit Testing Platform  
**Target Repository**: `patilanuja602/Testing_Agent`  

---

## 1. Executive Purpose

This document provides concrete, actionable engineering recommendations for our planned local Retrieval-Augmented Generation (RAG) system. Every recommendation in this report is directly derived from empirical failure modes (F01–F15) and retrieval requirements (R01–R10) documented during the 20-function GPU audit of Qwen2.5-Coder-7B.

The goal of our local RAG system is simple: **to supply the exact domain knowledge, control-flow constraints, and golden vectors that eliminate the model's 65% runtime failure rate and raise test suite pass rates above 90%.**

---

## 2. Target Knowledge Base & Indexing Strategy

The audit proved that standard text chunking (e.g. 500-token sliding windows) will fail for C/C++ unit test generation because code dependencies and execution guards are structural, not narrative.

### 2.1 Indexing Artifacts to Ingest:

```
┌────────────────────────────────────────────────────────────────────────┐
│ MULTI-LAYER LOCAL KNOWLEDGE BASE FOR C/C++ UNIT TESTING                │
├────────────────────────────────────────────────────────────────────────┤
│ Layer 1: Code AST & Symbols (Headers, Structs, Enums, Method Signatures)│
│ Layer 2: Control-Flow Graphs (Branch Precedence & Guard Sequences)     │
│ Layer 3: Domain Specifications (ICDs, CAN Framing, Protocols, Math)    │
│ Layer 4: Golden Test Vectors & Verified Calculation Oracles            │
│ Layer 5: Build Manifests (CMakeLists.txt, Link Flags, Dialect C++17)   │
└────────────────────────────────────────────────────────────────────────┘
```

#### Layer 1: Code AST & Type Signatures (R01, R02, R07)
- **Tooling**: Tree-sitter (C/C++) or Clang LibTooling.
- **What to Extract**:
  - Exact function signatures, return types, and parameter names.
  - Class definitions, private vs public members, constructor signatures.
  - **Virtuality specifier**: Explicitly index whether each method is `virtual`, `override`, or non-virtual (prevents F08 mock failures).
  - Transitive `#include` dependency trees (prevents F03 missing `<cmath>` failures).

#### Layer 2: Control-Flow Graph (CFG) Precedence (R05, R09)
- **What to Extract**:
  - The ordered hierarchy of conditional statements in the target function.
  - Precondition chains: e.g. For `Account::withdraw`:
    - `Guard 1: amount <= 0`
    - `Guard 2: amount > balance_`
    - `Guard 3: daily_withdrawn_ + amount > daily_limit_`
  - When the user asks to test Guard 3, the RAG engine automatically retrieves the required precondition: `amount <= balance_`.

#### Layer 3: Domain Specifications & Interface Control Documents (R03, R04, R08)
- **What to Ingest**:
  - Automotive communication specifications (CAN ID ranges, DLC sizes, alive counter rollover rules).
  - Sensor calibration datasheets (formula definitions, ADC resolution, voltage ranges).
  - Financial domain rules (interest day-count conventions, transaction fee tiers, cent integer representations).

#### Layer 4: Golden Test Vectors & Oracles (R08)
- **What to Ingest**:
  - Precomputed input-output tables for complex mathematical, bitwise, or cryptographic routines:
    - CRC-16-CCITT golden test vectors (payload `{0x01,0x02,0x03,0x04}` -> CRC `0x...`).
    - Cryptographic hash chaining test vectors.
    - Temperature formula conversion table at min, mid, and max ADC values.

---

## 3. Retrieval Strategy & Query Formulation

A naive semantic similarity search on code descriptions produces generic snippets. We recommend a **hybrid three-tier retrieval pipeline**:

```
[Target Function Query: "Test bank::Account::withdraw"]
                       │
       ┌───────────────┼───────────────┐
       ▼                               ▼
Tier 1: Symbol Resolver       Tier 2: Static CFG Analyzer
(Exact AST lookup for         (Extracts guard sequence:
class & method signature)      balance check precedes limit)
       │                               │
       └───────────────┬───────────────┘
                       │
                       ▼
              Tier 3: Domain Vector Search
              (Retrieves business rules, fee schedules,
               and golden test vectors)
                       │
                       ▼
           [Synthesized Context Pack]
```

### Retrieval Tiers:
1. **Tier 1 — Deterministic Symbol Extraction (No Vector DB needed)**:
   - Perform exact symbol lookup using Clang/Tree-sitter for the target function, its parent class, parameter structs, and enums. This is 100% accurate, instantaneous, and eliminates F01, F02, and F07.
2. **Tier 2 — Control-Flow Precedence Retrieval**:
   - Extract the guard conditions leading to each branch. Include this in prompt metadata: `"Precondition to reach Branch 3 (DAILY_LIMIT_EXCEEDED): amount <= balance && daily_withdrawn + amount > daily_limit"`. This directly neutralizes F05.
3. **Tier 3 — Hybrid BM25 + Dense Semantic Search**:
   - Search the project documentation, specification PDFs, and comments for keywords matching the function name and domain parameters. Retrieve relevant formulas and return code definitions.

---

## 4. Prompt Augmentation Patterns

The audit revealed that prompting the model to generate a single monolithic `int main()` that tests everything sequentially causes fatal state accumulation errors (F10).

We recommend an **enforced Prompt Engineering Standard** for the platform:

### 4.1 Enforce Multi-Function Test Isolation (Eliminating F10)
Instead of asking for a single `main()` function, the prompt must specify:
```
Generate separate, isolated test functions for each scenario:
void test_normal_operation();
void test_boundary_values();
void test_insufficient_funds();
void test_daily_limit_exceeded();

In each function, instantiate a fresh, independent object instance.
In int main(), call each test function sequentially.
```
By enforcing fresh object instantiation per test scenario, mutable state cannot leak across assertions, eliminating 100% of F10 failures.

### 4.2 Explicit Precondition and Invariant Injections (Eliminating F05 & F08)
Inject retrieved constraints directly into the prompt:
```
[RETRIEVED CONTEXT]
- Class bank::Account methods are NON-VIRTUAL. Do not create a mock subclass using 'override'.
- Branch execution order for withdraw(amount):
  1. amount <= 0 -> INVALID_AMOUNT
  2. amount > balance_ -> INSUFFICIENT_FUNDS
  3. daily_withdrawn_ + amount > daily_limit_ -> DAILY_LIMIT_EXCEEDED
- To test DAILY_LIMIT_EXCEEDED, you must ensure amount <= balance_ (e.g. balance=2000, daily_limit=500, withdraw=600).
```

### 4.3 Golden Test Vector Injection (Eliminating F04)
For mathematical or cryptographic functions:
```
[RETRIEVED GOLDEN VECTORS]
- For sensor_scale_temperature:
  raw_adc = 0    -> temp_c = -40.000 C
  raw_adc = 2048 -> temp_c = 124.864 C
  raw_adc = 4095 -> temp_c = 289.648 C
- For sensor_uart_crc16_verify:
  payload {0x01, 0x02, 0x03, 0x04} has CRC-16-CCITT = 0x93AC
```

---

## 5. Post-Generation Verification Gate

Even with RAG, an LLM remains a probabilistic token generator. The unit-testing platform must incorporate an automated local verification loop before returning code to the user:

```
[Model Generated Test]
         │
         ▼
[GCC / G++ Compile in Sandbox]
    ├── Compilation Failed ──> Auto-Inject Compiler Error & Request Repair
    └── Compilation Passed
         │
         ▼
[Execute Test Binary in Sandbox]
    ├── Return Code != 0 (SIGABRT / Crash) ──> Prune Failing Assertion / Repair
    └── Return Code == 0 (All Tests Passed)
         │
         ▼
[Gcov Coverage Instrumentation]
         │
         ▼
[Deliver Verified Test to User with Coverage Badge]
```

### Verification Gate Requirements:
1. **Never return uncompiled code**: If compilation fails, feed the GCC error message back into the model for a 1-turn targeted fix.
2. **Never return failing tests**: If a test assertion aborts with `SIGABRT`, isolate the failing assert, comment it with the actual observed return value, or discard the flawed case.
3. **Report Verified Coverage**: Compute and display exact Gcov line and branch coverage to the user as a verified metric.

---

## 6. Summary Implementation Roadmap for the Next Phase

| Phase | Milestone | Expected Outcome |
| :---: | :--- | :--- |
| **Phase 1** | Implement AST Symbol & Prototype Extractor (Clang / Tree-sitter) | 100% accurate signatures, headers, and virtuality resolution |
| **Phase 2** | Implement Control-Flow Guard & Precondition Analyzer | Elimination of execution-path masking (F05) |
| **Phase 3** | Ingest Domain Specs & Compute Mathematical Oracles | Elimination of arithmetic/CRC hallucinations (F04) |
| **Phase 4** | Deploy Multi-Function Isolated Prompt Templates | Elimination of sequential state accumulation (F10) |
| **Phase 5** | Connect Automated Sandbox Compilation & Execution Gate | Guaranteed 100% passing test suites delivered to users |

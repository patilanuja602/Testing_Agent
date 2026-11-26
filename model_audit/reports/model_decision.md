# Formal Model Adoption Decision: Qwen2.5-Coder-7B-Instruct

**Platform**: AI-Assisted C/C++ Cyclomatic Complexity Analysis and Unit Testing Platform  
**Target Model**: `Qwen2.5-Coder-7B-Instruct — Q4_K_M GGUF`  
**Model SHA-256**: `509287f78cb4d4cf6b3843734733b914b2c158e43e22a7f4bf5e963800894d3c`  
**Hardware Baseline**: NVIDIA GeForce RTX 4060 (8GB VRAM), CUDA 12.8, Linux x86_64  
**Date of Decision**: November 26, 2026  

---

## 1. Formal Verdict

### **VERDICT: CONDITIONAL APPROVAL**

The evaluation team has completed a rigorous, evidence-backed audit of `Qwen2.5-Coder-7B-Instruct` (Q4_K_M GGUF). Based on empirical results across 20 representative C and C++ benchmark functions:

The model is **APPROVED** as the primary local code-generation LLM for our C/C++ Unit-Testing Platform, **STRICTLY CONTINGENT UPON** the integration of our planned local Retrieval-Augmented Generation (RAG) system and automated test execution validation harness.

The model is **UNCONDITIONALLY REJECTED** for standalone, unassisted deployment as a test generator.

---

## 2. Summary of Empirical Justification

| Metric / Dimension | Target / Baseline | Measured Result | Evaluation Status |
| :--- | :--- | :--- | :--- |
| **Model File Integrity** | 100% Hash Match | `509287f7...` Exact Match | **SATISFIED** |
| **GPU Acceleration Speedup** | >= 10x Speedup | **61.29x** Prompt / **11.5x** Generation | **EXCEEDED** |
| **Inference Generation Speed** | >= 25 tokens/sec | **35.79** tokens/sec | **EXCEEDED** |
| **VRAM Consumption** | <= 7,000 MiB | **5,640** MiB (2.5 GiB buffer) | **SATISFIED** |
| **Syntactic Compilation Rate** | >= 85.0% | **90.0%** (18/20 passed GCC/G++) | **SATISFIED** |
| **Runtime Execution Pass Rate** | >= 80.0% | **35.0%** (7/20 passed execution) | **DEFICIENT (FAILED)** |
| **Fault / Mutation Sensitivity** | >= 80.0% | **100.0%** Mutation Kill Rate | **SATISFIED** |
| **Repeatability Across Seeds** | High Stability | 100% consistent across seeds | **SATISFIED** |

---

## 3. Core Strengths (Why Qwen2.5-Coder-7B is Retained)

1. **Hardware Fit**: Fits completely inside 8GB VRAM (5.6 GiB utilized with 28 layers fully offloaded), leaving 2.5 GiB for future embedding models or operating system buffers.
2. **Grammar and Compilation Fluency**: 90% compilation pass rate with zero syntax errors. Generates modern C99 and C++17 conforming code.
3. **Boundary Value Precision**: Strong intrinsic boundary analysis (correctly targets 0, 4095, -1, 4096, `LONG_MAX`, and two-sided interval boundaries).
4. **High Mutation Detection**: On valid tests, achieves 100% mutation kill rate against boundary shifts, logic inversions, and deleted checks.
5. **Deterministic Stability**: Reproduces stable test structures across multiple random seeds.

---

## 4. Fatal Weaknesses When Unassisted (Why RAG is Mandatory)

1. **Arithmetic & Domain Hallucinations (F04)**: Cannot evaluate floating-point formulas or bitwise CRC polynomials in its weights (asserted 0x1234 for CRC; asserted 500 instead of 50 for interest; asserted 0.0 C instead of 289.65 C).
2. **State Accumulation Blindness (F10)**: Sequential test statements emitted into a single `main()` function mutate object state, breaking preconditions for subsequent assertions (e.g. Account balance depleted to 100 before daily-limit test).
3. **Branch Precedence Masking (F05)**: Targets downstream branches while triggering upstream error guards first (e.g. passing NULL and 0 to test empty table, but hitting NULL check first).
4. **Mock Interface Hallucination (F08/F09)**: Assumes non-virtual methods are virtual when creating test doubles.

---

## 5. Mandatory Operational Conditions for Platform Integration

To adopt Qwen2.5-Coder-7B safely, the platform architecture must enforce the following four guardrails:

```
┌────────────────────────────────────────────────────────────────────────┐
│ MANDATORY PLATFORM INTEGRATION GUARDRAILS                              │
├────────────────────────────────────────────────────────────────────────┤
│ 1. RAG SPECIFICATION INJECTION:                                        │
│    Inject exact AST signatures (R01), header lists (R02), domain       │
│    formulas/vectors (R08), and branch precedence graphs (R09).         │
├────────────────────────────────────────────────────────────────────────┤
│ 2. PER-TEST CASE ISOLATION:                                            │
│    Enforce prompt templates that generate independent test functions   │
│    with fresh object instantiation, completely eliminating F10.        │
├────────────────────────────────────────────────────────────────────────┤
│ 3. TRANSLATION / CALCULATION ORACLE:                                   │
│    Precompute non-trivial values (CRCs, hashes, float scales) in the  │
│    RAG pipeline and supply them as golden assertions.                  │
├────────────────────────────────────────────────────────────────────────┤
│ 4. AUTOMATED EXECUTION GATE:                                           │
│    Compile and run all generated tests in a temporary sandbox. Any     │
│    test producing SIGABRT or failing assertions must be automatically  │
│    pruned or repaired before returning to the user.                    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Sign-off

- **Model Evaluation Lead**: Antigravity Autonomous Agent (DeepMind)
- **Status**: **APPROVED WITH CONDITIONS**
- **Next Phase**: Proceed immediately to the design and implementation of the local C/C++ RAG architecture.

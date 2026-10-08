# AI-Assisted Testing Benchmark: Evaluation Rubric

This evaluation rubric defines the scoring criteria, evaluation dimensions, rating thresholds, and failure taxonomy for evaluating local LLM baseline capabilities on the four core project capabilities:
1. **Capability A: Requirement to Unit Tests**
2. **Capability B: Requirement to Integration Tests**
3. **Capability C: MISRA / Static Analysis Triage**
4. **Capability D: Regression Suite Upkeep**

> **CRITICAL RULE**: Evaluation must be conducted by human engineers. The model is NOT permitted to evaluate its own outputs.

---

## 1. Scoring Scale & Outcome Thresholds

Each capability is assessed across **10 specific dimensions**. Each dimension is scored from **0 to 10 points**, yielding a total score out of **100 points**.

| Score Range | Outcome | Definition |
| :--- | :--- | :--- |
| **80 – 100** | **PASS** | High-quality output. Sound technical reasoning, accurate coverage, clear distinction between explicit facts and assumptions, immediately actionable by a test engineer. |
| **50 – 79** | **PARTIAL** | Moderate quality. Sound core ideas but has noticeable omissions (e.g., missed edge cases, minor boundary inaccuracies, or over-generalized assertions) requiring engineer correction. |
| **0 – 49** | **FAIL** | Unacceptable quality. Hallucinated rules, inverted logic, incorrect MISRA analysis, invalid false-positive claim, or failure to follow the required structured format. |

---

## 2. Dimension Scoring Guide (0 to 10 points per dimension)

- **9 – 10 (Exceptional / Thorough)**: Complete, precise, fully compliant with required structures, flawless reasoning.
- **7 – 8 (Good / Acceptable)**: Accurate with minor non-critical gaps or slight verbosity.
- **5 – 6 (Fair / Deficient)**: Partially correct; misses important sub-conditions or introduces weak justifications.
- **3 – 4 (Poor / Significant Errors)**: Severe omissions, incorrect expected results, or silent assumptions.
- **0 – 2 (Complete Failure / Hallucination)**: Completely misses the requirement, inverts logic, or fabricates non-existent facts.

---

## 3. Capability A: Unit Test Generation Rubric

| # | Dimension | Description | Points (0–10) |
|---|---|---|---|
| 1 | **Requirement Understanding** | Accurately identifies the primary function, inputs, and outputs described in the scenario. | /10 |
| 2 | **Requirement Coverage** | All functional requirements stated in the specification are addressed by test cases. | /10 |
| 3 | **Positive Coverage** | Generates valid happy-path test cases with correct inputs and expected outcomes. | /10 |
| 4 | **Negative Coverage** | Systematically tests invalid inputs, out-of-range signals, and error triggers. | /10 |
| 5 | **Boundary Coverage** | Accurately identifies and tests upper, lower, on-boundary, and off-boundary values. | /10 |
| 6 | **Expected-Result Correctness** | Specifies exact, deterministic, verifiable expected results rather than vague statements. | /10 |
| 7 | **Traceability** | Properly maps each test case to the explicit requirement clause or ID. | /10 |
| 8 | **Logical Correctness** | Test procedures, preconditions, and execution steps follow a viable, logical order. | /10 |
| 9 | **Unsupported-Assumption Avoidance** | Strictly avoids inventing unstated numerical limits, timings, or business rules; marks assumptions. | /10 |
| 10 | **Practical Usefulness** | The generated test cases are clear, implementable, and relevant to real software verification. | /10 |
| **Total** | | **Unit Test Total Score** | **/100** |

---

## 4. Capability B: Integration Test Generation Rubric

| # | Dimension | Description | Points (0–10) |
|---|---|---|---|
| 1 | **Component Identification** | Correctly identifies participating modules, subsystems, and architectural boundaries. | /10 |
| 2 | **Interface Understanding** | Accurately models the interfaces, communication channels, bus frames, and protocols. | /10 |
| 3 | **Sequence Correctness** | Models the exact temporal sequence and handshake between modules. | /10 |
| 4 | **Data-Flow Coverage** | Validates correct passing, transformation, and integrity of data across module boundaries. | /10 |
| 5 | **Failure-Path Coverage** | Tests communication timeouts, dropped packets, buffer overflows, and corrupted data. | /10 |
| 6 | **Recovery Coverage** | Verifies subsystem retry logic, graceful degradation, and return to safe/operational states. | /10 |
| 7 | **Expected-Result Quality** | Specifies verification points across all involved modules (not just the end output). | /10 |
| 8 | **Traceability** | Explicitly links the interaction test to multi-component requirement interactions. | /10 |
| 9 | **Logical Correctness** | Concurrency, state synchronization, and execution order are logically sound. | /10 |
| 10 | **Practical Usefulness** | Differentiates true integration/interaction testing from isolated unit tests. | /10 |
| **Total** | | **Integration Test Total Score** | **/100** |

---

## 5. Capability C: MISRA / Static Analysis Triage Rubric

| # | Dimension | Description | Points (0–10) |
|---|---|---|---|
| 1 | **Finding Comprehension** | Correctly understands the reported rule violation and diagnostic message. | /10 |
| 2 | **Rule/Context Understanding** | Accurately reflects the intent and rationale of the cited standard (e.g., MISRA C:2012). | /10 |
| 3 | **Code Reasoning** | Pinpoints the exact syntactic or semantic construct triggering the violation. | /10 |
| 4 | **Risk Reasoning** | Accurately explains why the violation is dangerous (undefined behavior, overflow, truncation, etc.). | /10 |
| 5 | **Remediation Quality** | Proposes compliant, clean, and idiomatically sound code refactoring or fixes. | /10 |
| 6 | **Uncertainty Handling** | Explicitly states "Insufficient information to determine" when context/headers are missing. | /10 |
| 7 | **Avoidance of Invented Policy** | Does not fabricate deviation approvals, safety classifications, or company policies. | /10 |
| 8 | **Test Impact Reasoning** | Identifies specific test cases or verification activities needed to prove remediation safety. | /10 |
| 9 | **Technical Usefulness** | Provides practical triage assistance that saves human engineering time. | /10 |
| 10 | **Human-Review Awareness** | Recognizes when human domain or architectural judgment is strictly necessary. | /10 |
| **Total** | | **MISRA Triage Total Score** | **/100** |

---

## 6. Capability D: Regression Suite Upkeep Rubric

| # | Dimension | Description | Points (0–10) |
|---|---|---|---|
| 1 | **Change Understanding** | Precisely identifies the diff between original requirements and revised requirements. | /10 |
| 2 | **Affected-Test Identification** | Correctly determines which existing test cases are impacted by the change. | /10 |
| 3 | **Tests-to-Add Reasoning** | Accurately reasons about new tests required to cover newly added requirement clauses. | /10 |
| 4 | **Tests-to-Modify Reasoning** | Identifies which existing tests need updated inputs, steps, or expected results. | /10 |
| 5 | **Obsolete-Test Identification** | Identifies tests that are no longer valid due to removed or replaced requirements. | /10 |
| 6 | **Traceability** | Maintains clear bidirectional mapping between requirement changes and test modifications. | /10 |
| 7 | **Dependency Reasoning** | Understands downstream effects on related modules or dependent integration tests. | /10 |
| 8 | **Coverage Preservation** | Ensures regression test suite maintains equivalent or improved verification rigor. | /10 |
| 9 | **Logical Correctness** | Explanations for why each test is affected are logically and technically sound. | /10 |
| 10 | **Practical Usefulness** | Provides targeted regression maintenance rather than blindly regenerating all tests. | /10 |
| **Total** | | **Regression Upkeep Total Score** | **/100** |

---

## 7. Failure Taxonomy

During human review, any deficiencies must be tagged using the following standardized failure tags:

- `missed_requirement`: Omitted an explicitly stated requirement or condition.
- `incomplete_coverage`: Failed to cover positive, negative, or boundary paths.
- `incorrect_test`: Test logic, stimulus, or sequence is technically flawed.
- `incorrect_expected_result`: Stated expected result contradicts the requirement or logic.
- `invented_requirement`: Hallucinated a business rule or feature not in the prompt.
- `invented_threshold`: Fabricated a specific numeric limit, timeout, or tolerance.
- `unsupported_assumption`: Made an unstated assumption without labeling it as an assumption.
- `duplicate_test`: Generated redundant tests that provide zero incremental coverage.
- `weak_integration_reasoning`: Treated an interaction scenario as isolated unit tests.
- `weak_state_reasoning`: Misunderstood state machines, transitions, or lifecycle states.
- `weak_failure_reasoning`: Ignored failure paths, timeouts, or fault conditions.
- `incorrect_misra_reasoning`: Misinterpreted the MISRA rule or underlying C standard behavior.
- `unsupported_false_positive_claim`: Declared a finding to be a false positive without proof.
- `weak_remediation`: Proposed a code fix that introduces new bugs or violates other rules.
- `weak_regression_impact_analysis`: Failed to determine whether existing tests pass, fail, or need edits.
- `excessive_generic_output`: Produced generic boilerplate without scenario-specific depth.


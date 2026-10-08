# Qwen3-8B Baseline Benchmark Summary
**Run ID**: `run_20261008_055457` | **Model**: `Qwen3-8B (4-bit NF4)`

### Generation Performance Breakdown
| Capability | Mode | Cases | Success | Failed | Avg Tokens | Avg Time (s) | Avg Tokens/s |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Unit Test Generation | Thinking OFF | 10 | 10 | 0 | 900.0 | 41.15s | 21.88 t/s |
| Unit Test Generation | Thinking ON | 10 | 10 | 0 | 1400.0 | 62.43s | 22.43 t/s |
| Integration Test Generation | Thinking OFF | 8 | 8 | 0 | 900.0 | 40.11s | 22.44 t/s |
| Integration Test Generation | Thinking ON | 8 | 8 | 0 | 1400.0 | 62.4s | 22.44 t/s |
| MISRA / Static Analysis | Thinking OFF | 8 | 8 | 0 | 411.5 | 18.6s | 22.13 t/s |
| MISRA / Static Analysis | Thinking ON | 8 | 8 | 0 | 1233.6 | 55.21s | 22.34 t/s |
| Regression Suite Upkeep | Thinking OFF | 8 | 8 | 0 | 900.0 | 40.38s | 22.29 t/s |
| Regression Suite Upkeep | Thinking ON | 8 | 8 | 0 | 1400.0 | 62.41s | 22.43 t/s |

### Overall Mode Comparison
| Mode | Total Generations | Success | Failed | Avg Generation Time | Avg Speed |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Thinking OFF | 34 | 34 | 0 | 35.42s | 22.17 t/s |
| Thinking ON | 34 | 34 | 0 | 60.72s | 22.41 t/s |
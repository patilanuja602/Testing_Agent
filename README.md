# Testing_Agent: AI-Assisted Software Testing & Verification System

An AI-powered software testing and verification engine powered locally by **Qwen3-8B** (using 4-bit NF4 BitsAndBytes quantization).

This system provides automated derivation, evaluation, and benchmark analysis across four core testing capabilities:
1. **Unit Test Generation** — Deriving boundary, edge-case, and functional unit tests from formal requirements.
2. **Integration Test Generation** — Cross-component, timing, bus failure, and interface protocol testing.
3. **Static Analysis & MISRA Triage** — Finding explanation, risk analysis, false-positive detection, and compliant remediation.
4. **Regression Suite Upkeep** — Change impact analysis, test suite delta identification, and retirement of obsolete tests.

---

## Repository Structure

```
Testing_Agent/
├── .gitignore                      # Git ignore rules (excludes .venv, model weights, caches)
├── README.md                       # Main project overview & instructions
└── qwen_test_generator/            # Application core package
    ├── app.py                      # Interactive Streamlit Web UI
    ├── requirements.txt            # Python dependencies
    ├── smoke_test.py               # Quick validation & hardware sanity test
    ├── model/                      # Model loader (4-bit NF4 BitsAndBytes GPU loader)
    │   └── model_loader.py
    ├── generation/                 # Prompt construction & generation pipeline
    │   ├── generator.py
    │   └── prompt_template.py
    ├── evaluation/                 # Experiment logging & recording utilities
    │   └── save_results.py
    ├── benchmark/                  # Benchmark suite & evaluation tooling
    │   ├── project_test_cases.json # 34 standardized evaluation scenarios
    │   ├── evaluation_rubric.md    # Multi-dimensional scoring rubric
    │   ├── run_benchmark.py        # Benchmark execution runner
    │   ├── evaluate_results.py     # Automated evaluation & scoring script
    │   └── results/                # Recorded evaluation results & summaries
    ├── prompts/                    # System prompts and templates
    └── outputs/                    # Local experiment generation records
```

---

## Hardware & Environment Requirements

- **GPU:** NVIDIA GPU with $\ge$ 8 GB VRAM (e.g., NVIDIA RTX 4060)
- **RAM:** 16 GB+ System RAM
- **OS:** Linux (Ubuntu 20.04+ or similar)
- **Python:** 3.10+
- **CUDA:** 12.1+ / 12.6

---

## Quickstart

### 1. Set Up Virtual Environment & Dependencies

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install PyTorch with CUDA support (e.g. CUDA 12.6 or CUDA 12.4)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126

# Install remaining dependencies
pip install -r qwen_test_generator/requirements.txt
```

### 2. Download the Model

Download the official `Qwen/Qwen3-8B` model weights:

```bash
pip install -U "huggingface_hub[cli]"
hf download Qwen/Qwen3-8B --local-dir qwen_test_generator/models/Qwen3-8B
```

*Note: The model weights (~16 GB) remain stored locally and are excluded from version control.*

### 3. Verify Hardware & Pipeline

Run the smoke test to verify CUDA GPU detection and 4-bit quantization loading:

```bash
python qwen_test_generator/smoke_test.py
```

### 4. Launch the Interactive Web Application

```bash
cd qwen_test_generator
streamlit run app.py
```

### 5. Run the Benchmark Suite

Execute the standardized 34-scenario evaluation:

```bash
python qwen_test_generator/benchmark/run_benchmark.py
```

Evaluate and score the run:

```bash
python qwen_test_generator/benchmark/evaluate_results.py
```

---

## License

This project is licensed under the Apache 2.0 License.

# Qwen3-8B Baseline Test-Case Generator (Phase 1)

## 1. Purpose
Measure how well the **base** Qwen3-8B model can discover useful software test cases from a short natural-language scenario, with nothing else around it.

## 2. Why baseline before fine-tuning
Without a baseline, any later gain from RAG or LoRA/QLoRA is unmeasurable. This app records exactly what the untouched model does, under exact, reproducible settings.
There is **no domain logic** in the code. The only guidance the model gets is `prompts/baseline_prompt.txt`, which is domain-neutral. Edit that file deliberately and treat each change as a new experiment (its SHA-256 is stored in every result).

## 3. Installation
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```
Install a CUDA build of PyTorch appropriate for your driver first if needed (https://pytorch.org).

## 4. Model setup
Download once (on a machine with internet), then everything runs offline:
```bash
pip install -U "huggingface_hub[cli]"
hf download Qwen/Qwen3-8B --local-dir ./models/Qwen3-8B
```
Or set `QWEN_MODEL_PATH=/path/to/Qwen3-8B`. The app sets `HF_HUB_OFFLINE=1` and loads with `local_files_only=True`; no data leaves the machine.
Memory: In 4-bit mode (NF4 with BitsAndBytes), Qwen3-8B requires ~5.5GB GPU VRAM, fitting easily within an 8GB RTX 4060.

## 5. Run
```bash
streamlit run app.py
```

## 6. Entering a scenario
Type it into the Scenario box, adjust parameters in the sidebar, click **GENERATE TEST CASES**.

## 7. Saved experiments
Click **SAVE EXPERIMENT** -> `outputs/experiment_001.json`, `experiment_002.json`, ... (never overwritten). Each file has: id, UTC timestamp, model, path, precision, temperature, top_p, top_k, max_new_tokens, seed, thinking flag, scenario, exact prompt + prompt file hash + fully rendered chat prompt, complete raw output, status/errors, parsed output and `parsed_test_cases`, library versions. If parsing fails the raw output is still saved.

## 8. Limitations
- Output is requested as JSON; very long outputs can be truncated at `max_new_tokens` (flagged, raw kept).
- Sampling with a seed is reproducible only on the same hardware/software stack; use temperature 0 for greedy decoding.
- No automatic scoring. Evaluation is manual for now.
- Single request at a time, no streaming.

## 9. Future phases (NOT implemented)
1. Base Qwen3-8B evaluation (this app)
2. Company project/rules RAG
3. LoRA/QLoRA fine-tuning on company examples
4. Evaluation and comparison
5. Specialized second model/agent
6. Execution / mutation / browser / API testing

## Extension points
- RAG: add `retrieval/` and have `generation/generator.py` accept extra context passed into `build_prompt`.
- LoRA: add an optional `adapter_path` to `load_model` (PEFT `PeftModel.from_pretrained`) and record it in the experiment JSON.
- Agents: add a `pipeline` layer that calls `generate_test_cases` as one step.

"""Streamlit UI for the Qwen3-8B baseline test-case generator.   Run: streamlit run app.py"""
import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import json
import streamlit as st

import torch
from pathlib import Path
from model.model_loader import DEFAULT_MODEL_PATH, load_model, describe_device, ModelLoadError
from generation.generator import GenerationParams, generate_test_cases
from generation.prompt_template import PROMPT_PATH
from evaluation.save_results import save_experiment


st.set_page_config(page_title="Qwen3-8B Baseline Test Generator", layout="wide")
st.title("Qwen3-8B Baseline - Test Case Generator")
st.caption("Phase 1 baseline: no RAG, no fine-tuning, no agents. Everything runs locally.")


@st.cache_resource(show_spinner="Loading Qwen3-8B from local disk (first time takes a while)...")
def get_model(path, quant):
    return load_model(path, quant)


with st.sidebar:
    st.header("Configuration")
    model_path = st.text_input("Local model path", DEFAULT_MODEL_PATH)
    MODEL_NAME = Path(model_path).expanduser().name or "Qwen3-8B"
    st.markdown(f"**Model:** {MODEL_NAME}")
    st.markdown(f"**Device:** {describe_device()}")
    quant = st.selectbox(
        "Precision",
        ["4bit", "8bit", "none"],
        index=0,
        help="'4bit' = bitsandbytes NF4 (recommended for RTX 4060). 'none' = bf16."
    )
    st.divider()
    temperature = st.number_input("Temperature (0 = greedy)", 0.0, 2.0, 0.7, 0.05)
    top_p = st.number_input("top_p", 0.0, 1.0, 0.8, 0.05)
    top_k = st.number_input("top_k", 0, 200, 20, 1)
    max_new_tokens = st.number_input("Max new tokens", 256, 32000, 6000, 256)
    seed = st.number_input("Seed", 0, 2**31 - 1, 42, 1)
    enable_thinking = st.checkbox("Qwen3 thinking mode", value=False)
    timeout_s = st.number_input("Timeout (seconds)", 30, 7200, 900, 30)

scenario = st.text_area("Scenario", height=200, placeholder="Enter software/project scenario...")

if st.button("GENERATE TEST CASES", type="primary"):
    if not scenario.strip():
        st.warning("Please enter a scenario first.")
    else:
        try:
            model, tokenizer = get_model(model_path, quant)
        except ModelLoadError as e:
            st.error(f"{type(e).__name__}: {e}")
            st.stop()
        except Exception as e:  # noqa: BLE001
            st.error(f"Unexpected model loading failure: {type(e).__name__}: {e}")
            st.stop()
        params = GenerationParams(float(temperature), float(top_p), int(top_k), int(max_new_tokens),
                                  int(seed), bool(enable_thinking), int(timeout_s))
        with st.spinner("Generating..."):
            res = generate_test_cases(model, tokenizer, scenario, params)
        st.session_state["last"] = dict(res=res, scenario=scenario, params=params.to_dict(),
                                        model_path=model_path, quant=quant)
        st.session_state.pop("saved_path", None)

last = st.session_state.get("last")
if last:
    res = last["res"]
    st.divider()
    st.caption(f"Status: {res['status']} | tokens: {res['generated_tokens']} | {res['duration_seconds']}s")
    if res["error"]:
        st.error(res["error"])
    if res["parse_error"]:
        st.warning(f"Parsing problem: {res['parse_error']}  - raw output is preserved below and will be saved.")

    p = res["parsed"] or {}

    def bullets(title, key):
        st.subheader(title)
        items = p.get(key)
        if isinstance(items, list) and items:
            for i in items:
                st.markdown(f"- {i}")
        else:
            st.caption("(none / not parsed)")

    st.subheader("Scenario Understanding")
    st.write(p.get("scenario_understanding") or "(not parsed)")
    bullets("Explicit Requirements", "explicit_requirements")
    bullets("Logical Invariants", "logical_invariants")
    bullets("Domain Expectations", "domain_expectations")
    bullets("Assumptions Requiring Confirmation", "assumptions_requiring_confirmation")

    tcs = res["parsed_test_cases"]
    st.subheader(f"Generated Test Cases ({len(tcs)})")
    for tc in tcs:
        if not isinstance(tc, dict):
            st.code(json.dumps(tc, indent=2, ensure_ascii=False)); continue
        label = f"{tc.get('test_case_id', '?')} - {tc.get('title', '')}  [{tc.get('requirement_source', '?')} | {tc.get('test_type', '?')} | {tc.get('priority', '?')}]"
        with st.expander(label):
            for k in ["requirement_category", "requirement_source", "preconditions", "test_data"]:
                st.markdown(f"**{k.replace('_', ' ').title()}:** {tc.get(k, '')}")
            steps = tc.get("steps", [])
            st.markdown("**Steps:**")
            for i, s in enumerate(steps if isinstance(steps, list) else [steps], 1):
                st.markdown(f"{i}. {s}")
            for k in ["expected_result", "priority", "test_type", "reasoning_coverage"]:
                st.markdown(f"**{k.replace('_', ' ').title()}:** {tc.get(k, '')}")

    st.subheader("Coverage Summary")
    st.write(p.get("coverage_summary") or "(not parsed)")

    with st.expander("Raw model output (always preserved)"):
        st.text(res["raw_output"])

    st.divider()
    if st.button("SAVE EXPERIMENT"):
        path = save_experiment(model_name=MODEL_NAME, model_path=last["model_path"], quantization=last["quant"],
                               params=last["params"], scenario=last["scenario"], result=res,
                               prompt_file=PROMPT_PATH)
        st.session_state["saved_path"] = str(path)
    if st.session_state.get("saved_path"):
        st.success(f"Saved to {st.session_state['saved_path']}")

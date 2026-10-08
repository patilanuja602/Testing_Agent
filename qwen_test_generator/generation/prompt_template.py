"""Loads the baseline prompt file and injects the scenario. No domain logic lives here."""
from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "baseline_prompt.txt"


def load_template(path: Path = PROMPT_PATH) -> str:
    return Path(path).read_text(encoding="utf-8")


def build_prompt(scenario: str, path: Path = PROMPT_PATH) -> str:
    # Plain replace (not str.format) because the template contains JSON braces.
    return load_template(path).replace("{{SCENARIO}}", scenario.strip())

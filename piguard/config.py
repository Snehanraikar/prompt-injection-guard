"""Central configuration: paths, Kaggle handles, and model settings."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Keep every download/cache inside the project folder (self-contained environment).
CACHE_DIR = ROOT / ".cache"
os.environ.setdefault("KAGGLEHUB_CACHE", str(CACHE_DIR / "kagglehub"))
os.environ.setdefault("HF_HOME", str(CACHE_DIR / "huggingface"))
os.environ.setdefault("TORCH_HOME", str(CACHE_DIR / "torch"))
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
DATA_RAW = ROOT / "data" / "raw"
DATA_PROC = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
RESULTS_DIR = ROOT / "results"
for _d in (DATA_RAW, DATA_PROC, MODELS_DIR, RESULTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SEED = 42

# Kaggle datasets used for the content (Layer-1) detector.
# value = (local folder name, files to keep)
KAGGLE_DATASETS = {
    "chuneeb/ai-agent-cybersecurity-dataset-2026": (
        "chuneeb_ai-agent-cybersecurity-dataset-2026",
        ["data/threat_intelligence/hf_prompt_injections.csv"],
    ),
    "krishnayadav456wrsty/prompt-injection-and-jailbreak-detection-dataset": (
        "krishnayadav456wrsty_prompt-injection-and-jailbreak-detection-dataset",
        ["prompt_injection_detection_dataset.csv", "update1357.csv", "v3update20001.csv"],
    ),
    "mohammedaminejebbar/malicious-prompt-detection-dataset-mpdd": (
        "mohammedaminejebbar_malicious-prompt-detection-dataset-mpdd",
        ["MPDD.csv"],
    ),
    # Small, independently written set -> used only as an out-of-distribution test.
    "abdul5445/llm-prompt-injection-classification-dataset": (
        "abdul5445_llm-prompt-injection-classification-dataset",
        ["prompt_injection_dataset.csv"],
    ),
}

# Benchmark prompt-injection detectors hosted on Kaggle Models.
# injection score = 1 - P(benign-like labels), so 2- and 3-class heads both work.
KAGGLE_MODELS = {
    "protectai_deberta_v2": "aisuko/deberta-v3-base-prompt-injection-v2/transformers/default",
    "wolf_defender": "aisuko/wolf-defender-prompt-injection/transformers/default",
    # Gated: needs Kaggle credentials + accepted Llama licence. Skipped if unavailable.
    "prompt_guard_86m": "metaresearch/llama-3.1-prompt-guard/transformers/86m",
}

# Agent-trace benchmark used for the behavioural (Layer-2) monitor.
INJECAGENT_URL = "https://raw.githubusercontent.com/uiuc-kang-lab/InjecAgent/main/data/"
INJECAGENT_FILES = [
    "attacker_cases_dh.jsonl", "attacker_cases_ds.jsonl", "attacker_simulated_responses.json",
    "test_cases_dh_base.json", "test_cases_ds_base.json",
    "test_cases_dh_enhanced.json", "test_cases_ds_enhanced.json",
    "tools.json", "user_cases.jsonl",
]
INJECAGENT_DIR = DATA_RAW / "injecagent"

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
HF_MAX_LENGTH = 512
HF_BATCH_SIZE = 16

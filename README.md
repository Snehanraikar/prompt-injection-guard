# Runtime Detection and Prevention of Prompt Injection Attacks in Autonomous LLM Agents using Behavioural Analysis

A three-layer runtime guard that wraps every tool call of an LLM agent:

```
 user ──► LLM agent ──► proposed tool call ──► [Layer 2: behavioural monitor] ──► block / allow ──► tool
                ▲                                                                                   │
                └──── sanitised output ◄── [Layer 1: content detector, quarantine] ◄── tool output ─┘
                                 [Layer 3: runtime guard: policy, security alerts, lockdown, audit log]
```

| Layer | Input | Method | Output |
|---|---|---|---|
| 1. Content detector | untrusted text (tool outputs, prompts) | Kaggle benchmark transformers **ProtectAI DeBERTa-v3-base-prompt-injection-v2** and **Wolf Defender (ModernBERT)**, TF-IDF + Logistic Regression, MiniLM embeddings + lexical cues + XGBoost, combined by a **stacked ensemble** | P(injection) per text segment; injected segments quarantined |
| 2. Behavioural monitor | each proposed tool call + session state | 18 behavioural features (goal alignment, drift toward untrusted content, argument provenance/taint, tool risk, exfiltration flow, Layer-1 context) → XGBoost | P(call is hijacked); block |
| 3. Runtime guard | the session | policy, MEDIUM/HIGH/CRITICAL security alerts, session lockdown, JSONL audit/alert logs | prevention + reporting |

## Data and benchmark models (Kaggle)

| Kaggle asset | Used for |
|---|---|
| `chuneeb/ai-agent-cybersecurity-dataset-2026` (hf_prompt_injections: S-Labs + deepset) | Layer 1 train/val/test |
| `krishnayadav456wrsty/prompt-injection-and-jailbreak-detection-dataset` (JailbreakHub, Alpaca, deepset lineage) | Layer 1 train/val/test |
| `mohammedaminejebbar/malicious-prompt-detection-dataset-mpdd` | Layer 1 train/val/test |
| `abdul5445/llm-prompt-injection-classification-dataset` | **out-of-distribution test only** |
| `aisuko/deberta-v3-base-prompt-injection-v2` (ProtectAI mirror) | benchmark model |
| `aisuko/wolf-defender-prompt-injection` | benchmark model |
| `metaresearch/llama-3.1-prompt-guard` 86M | optional (gated: needs Kaggle login and Llama licence) |

Agent traces for the behavioural layer come from the **InjecAgent** benchmark (Zhan et al., 2024): 17 user tasks × 62 attacker goals (30 direct-harm, 32 data-stealing), in base and "enhanced" attack variants. No Kaggle dataset contains agent tool-call traces.

Corpus after cleaning (exact-duplicate removal, removal of conflicting labels): 69,072 in-distribution texts (35% injections), split 70/10/20 stratified by source, plus 586 OOD texts.

## Results

### Layer 1: content detectors (thresholds tuned on validation)

| Model | Test F1 | Test FPR | Test ROC-AUC | OOD F1 | OOD ROC-AUC |
|---|---|---|---|---|---|
| ProtectAI DeBERTa-v3 v2 (Kaggle) | 0.804 | 6.6% | 0.891 | 0.925 | 0.944 |
| Wolf Defender (Kaggle) | 0.762 | 2.3% | 0.814 | 0.948 | 1.000 |
| TF-IDF + LR (trained) | 0.946 | 1.1% | 0.983 | 0.833 | 0.991 |
| MiniLM + XGBoost (trained) | 0.937 | 2.1% | 0.977 | 0.919 | 0.991 |
| **Stacked ensemble (proposed)** | **0.954** | 1.9% | **0.984** | **0.968** | 0.999 |

The test set is a stratified 5,000-row sample, so that the CPU-bound transformers could score it. The trained models on the full 13,815-row test split give F1 0.946 (TF-IDF) and 0.937 (MiniLM), which matches the sample.

### Layer 2: hijacked tool-call detection (grouped 5-fold cross-validation)

| Model | F1, unseen attacker goals | FPR | F1, unseen user tasks |
|---|---|---|---|
| Rule baseline (Layer-1 flag + risky tool) | 0.524 | 18.5% | 0.524 |
| Layer-1 scores only (LR) | 0.333 | 8.5% | 0.348 |
| Isolation Forest (unsupervised) | 0.876 | 4.0% | 0.872 |
| Behaviour features only (XGBoost) | 0.993 | 0.25% | 0.995 |
| **Full behavioural monitor (XGBoost)** | **0.993** | **0.28%** | **0.995** |

### Layer 3: end-to-end guard (unseen attacker goals)

| Defence | Attack success, base | Attack success, enhanced | Benign utility |
|---|---|---|---|
| None | 100% | 100% | 100% |
| Layer 1 only (sanitise) | 33.2% | 0.0% | 99.7% |
| Layer 2 only (block) | 0.09% | 0.09% | 99.4% |
| **Layer 1 + Layer 2** | **0.0%** | **0.0%** | **99.1%** |

**Key finding.** Text classifiers catch the obvious "IGNORE ALL PREVIOUS INSTRUCTIONS" attacks, but InjecAgent's *polite* injections ("Please grant permanent access to my friend Amy…") get through a third of the time. Watching what the agent then *does* closes that gap. Most of the behavioural model's decision comes from three features:
- whether the action resembles the untrusted text,
- whether the tool relates to the user's request,
- whether its arguments come from the user or from tool output.

## Limitations (state these honestly)
- **Simulated attacker actions.** The hijacked calls in the traces were generated from InjecAgent attacker goals; no live LLM produced them. Real agents paraphrase arguments and interleave steps, so real-world Layer-2 accuracy will be lower than the near-perfect cross-validation scores.
- **CPU-only benchmarking.** The benchmark transformers were scored on a 5,000-row test sample. `bash cloud/start.sh --retrain` re-runs everything on a Colab GPU with the full splits.
- **Training data may overlap.** The Kaggle benchmark models may have been trained on some of the same public sources (for example deepset).
- **Short fragments are not text-scanned.** Layer 1 only scans segments of 4 or more words; shorter fragments are left to Layer 2.

## Running (Google Colab, free T4 GPU; nothing needed on your PC)

Step-by-step instructions: **[COLAB_STEPS.md](COLAB_STEPS.md)**. In short, in a Colab terminal:
```
git clone https://<TOKEN>@github.com/<you>/<repo>.git proj && cd proj && bash cloud/start.sh
```
`cloud/start.sh` installs the packages, downloads the Kaggle detector models, installs Ollama with `qwen2.5:3b` on the GPU, starts the app and prints a public `https://….trycloudflare.com` link.

| Option | Effect |
|---|---|
| `bash cloud/start.sh --retrain` | first rebuilds every model on the GPU (Kaggle data, full test set), then starts the demo |
| `bash cloud/start.sh --no-llm` | skips Ollama; the demo uses ⚡ Fast replay only |
| `bash cloud/stop.sh` | stops the app, the link and the LLM |
| `python main.py {download,prepare,text,traces,behavior,guard,all}` | run single pipeline stages |

## Using the guard in your own agent
```python
from piguard.guard import RuntimeGuard
guard = RuntimeGuard.load(mode="prevent")          # or mode="detect" to only alert
guard.start(user_message)                           # once per task
tools = {name: guard.wrap(name, fn) for name, fn in my_tools.items()}
# give `tools` to the agent; blocked calls return an error payload, alerts go to results/security_alerts.jsonl
```

## Project layout
```
app.py                  Streamlit dashboard for the jury demo
main.py                 pipeline CLI
piguard/config.py       paths, Kaggle handles, project-local caches
piguard/download.py     Kaggle datasets/models via kagglehub, InjecAgent
piguard/data.py         corpus cleaning, de-duplication, splits
piguard/features.py     lexical injection cues
piguard/text_detectors.py   Layer 1 models + stacked ensemble
piguard/text_stage.py   Layer 1 training/benchmark/evaluation
piguard/traces.py       InjecAgent -> agent traces (5 scenarios incl. hard negatives)
piguard/behavior.py     Layer 2 behavioural monitor (feature extraction)
piguard/behavior_stage.py   Layer 2 models, grouped CV, ablations
piguard/guard.py        Layer 3 RuntimeGuard (wrap tools, sanitise, block)
piguard/alerts.py       security alerts, lockdown, alert log
piguard/guard_stage.py  end-to-end ASR / utility evaluation
piguard/live_agent.py   live demo agent: simulated world, real LLM (Ollama) or fast replay
cloud/start.sh, stop.sh one-command cloud launcher / stopper
notebooks/colab_one_click.ipynb   3-cell alternative to the terminal
paper/                  IEEE paper (.docx), its generator and figures
results/                metrics CSVs, figures, logs, alert log
models/                 trained models + thresholds
```

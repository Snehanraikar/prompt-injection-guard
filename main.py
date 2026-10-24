"""Runtime detection & prevention of prompt injection in LLM agents - pipeline CLI.

    python main.py download        # Kaggle datasets + Kaggle benchmark models + InjecAgent
    python main.py prepare         # build the unified text corpus
    python main.py text            # Layer 1: train + benchmark + stacked ensemble
    python main.py traces          # build agent traces from InjecAgent
    python main.py behavior        # Layer 2: behavioural monitor (grouped CV, ablations)
    python main.py guard           # Layer 3: end-to-end runtime guard evaluation (ASR vs utility)
    python main.py all

The live demo is the Streamlit app (app.py), started in the cloud by cloud/start.sh.
"""
import argparse
import warnings

warnings.filterwarnings("ignore")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["download", "prepare", "text", "traces", "behavior", "guard", "all"])
    ap.add_argument("--bench-test-n", type=int, default=5000, help="test rows scored by benchmark transformers")
    ap.add_argument("--bench-val-n", type=int, default=3000, help="val rows used to fit the stacker")
    ap.add_argument("--obs-detector", default="stacked_ensemble",
                    help="Layer-1 model used to score tool outputs inside the behavioural monitor")
    a = ap.parse_args()
    stages = ["download", "prepare", "text", "traces", "behavior", "guard"] if a.stage == "all" else [a.stage]

    for s in stages:
        print(f"\n===== {s} =====")
        if s == "download":
            from piguard.download import download_all
            download_all()
        elif s == "prepare":
            from piguard.data import build_corpus
            build_corpus()
        elif s == "text":
            from piguard import text_stage
            text_stage.run(a.bench_test_n, a.bench_val_n)
        elif s == "traces":
            from piguard import traces
            traces.build_traces()
        elif s == "behavior":
            from piguard import behavior_stage
            behavior_stage.run(a.obs_detector)
        elif s == "guard":
            from piguard import guard_stage
            guard_stage.run()


if __name__ == "__main__":
    main()

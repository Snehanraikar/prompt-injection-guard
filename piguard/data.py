"""Build one clean, de-duplicated prompt-injection corpus from the Kaggle datasets."""
import re

import pandas as pd
from sklearn.model_selection import train_test_split

from . import config as C

CORPUS_PATH = C.DATA_PROC / "text_corpus.csv"


def _norm(t):
    return re.sub(r"\s+", " ", str(t)).strip()


def _krish_source(s):
    s = str(s)
    if "Alpaca" in s:
        return "krish:alpaca"
    if "JailbreakHub" in s:
        return "krish:jailbreakhub"
    if "deepset" in s or "Denzel" in s:
        return "krish:deepset-lineage"
    return "krish:other"


def load_raw():
    frames = []

    d = C.DATA_RAW / "chuneeb_ai-agent-cybersecurity-dataset-2026/data/threat_intelligence/hf_prompt_injections.csv"
    df = pd.read_csv(d)
    frames.append(pd.DataFrame({
        "text": df.text, "label": df.label.astype(int),
        "source": "hf:" + df.source_dataset.str.split("/").str[0]}))

    kdir = C.DATA_RAW / "krishnayadav456wrsty_prompt-injection-and-jailbreak-detection-dataset"
    kd = pd.concat([pd.read_csv(kdir / f) for f in
                    ("v3update20001.csv", "update1357.csv", "prompt_injection_detection_dataset.csv")])
    frames.append(pd.DataFrame({
        "text": kd.text, "label": (kd.label == "injection").astype(int),
        "source": kd.source.map(_krish_source)}))

    md = pd.read_csv(C.DATA_RAW / "mohammedaminejebbar_malicious-prompt-detection-dataset-mpdd/MPDD.csv")
    frames.append(pd.DataFrame({"text": md.Prompt, "label": md.isMalicious.astype(int), "source": "mpdd"}))

    ad = pd.read_csv(C.DATA_RAW / "abdul5445_llm-prompt-injection-classification-dataset/prompt_injection_dataset.csv")
    frames.append(pd.DataFrame({
        "text": ad.text, "label": (ad.label_name != "Benign").astype(int), "source": "ood:abdul5445"}))
    return pd.concat(frames, ignore_index=True)


def build_corpus(seed=C.SEED):
    df = load_raw()
    df["text"] = df.text.map(_norm)
    df = df[df.text.str.len() >= 3]
    df["key"] = df.text.str.lower()

    # Same text with contradicting labels across datasets -> unreliable, drop all copies.
    conflict = df.groupby("key").label.nunique()
    df = df[~df.key.isin(conflict[conflict > 1].index)]
    # OOD rows win ties so the OOD test set never overlaps the training data.
    df["_ood"] = df.source.str.startswith("ood:")
    df = df.sort_values("_ood", ascending=False, kind="stable").drop_duplicates("key").drop(columns="_ood")

    ood = df[df.source.str.startswith("ood:")].assign(split="ood_test")
    ind = df[~df.source.str.startswith("ood:")]
    strat = ind.source + "|" + ind.label.astype(str)
    rare = strat.map(strat.value_counts()) < 20
    strat = strat.where(~rare, "rare|" + ind.label.astype(str))
    tr, rest = train_test_split(ind, test_size=0.30, stratify=strat, random_state=seed)
    va, te = train_test_split(rest, test_size=2 / 3, stratify=strat.loc[rest.index], random_state=seed)
    out = pd.concat([tr.assign(split="train"), va.assign(split="val"), te.assign(split="test"), ood])
    out = out.drop(columns="key").reset_index(drop=True)
    out.to_csv(CORPUS_PATH, index=False)

    summary = out.groupby(["split", "source"]).label.agg(n="size", injections="sum")
    print(summary.to_string())
    print(out.groupby("split").label.agg(n="size", pos_rate="mean").to_string())
    return out


def load_corpus():
    if not CORPUS_PATH.exists():
        return build_corpus()
    return pd.read_csv(CORPUS_PATH, keep_default_na=False)

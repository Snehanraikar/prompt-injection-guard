"""Stage 1: train / benchmark / ensemble the content (prompt-text) detectors."""
import json

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict

from . import config as C
from . import plots
from .data import load_corpus
from .metrics import best_f1_threshold, binary_report
from .text_detectors import (EmbedXGBDetector, StackedEnsemble, TfidfDetector, _logit,
                             load_benchmark_detectors, save)


def _strat_sample(df, n, seed=C.SEED):
    if len(df) <= n:
        return df
    key = df.source + "|" + df.label.astype(str)
    frac = n / len(df)
    return (df.groupby(key, group_keys=False)
              .apply(lambda g: g.sample(max(1, round(len(g) * frac)), random_state=seed)))


def run(bench_test_n=5000, bench_val_n=3000, benchmarks=None):
    df = load_corpus()
    tr, va, te, ood = (df[df.split == s] for s in ("train", "val", "test", "ood_test"))
    va_b, te_b = _strat_sample(va, bench_val_n), _strat_sample(te, bench_test_n)
    print(f"train={len(tr)} val_bench={len(va_b)} test_full={len(te)} test_bench={len(te_b)} ood={len(ood)}")

    print("[text] training TF-IDF + LR ...")
    tfidf = TfidfDetector().fit(tr.text, tr.label.values)
    save(tfidf, "tfidf_lr")
    print("[text] training MiniLM-embedding + XGBoost ...")
    exgb = EmbedXGBDetector().fit(tr.text, tr.label.values)
    save(exgb, "minilm_xgb")

    members = {"tfidf_lr": tfidf, "minilm_xgb": exgb}
    members.update(load_benchmark_detectors(benchmarks))
    print("[text] members:", list(members))

    sets = {"val": va_b, "test": te_b, "ood": ood}
    S = {}
    for split, d in sets.items():
        S[split] = {}
        for n, m in members.items():
            print(f"[text] scoring {n} on {split} ({len(d)})")
            S[split][n] = m.predict_proba(d.text.tolist())

    ens = StackedEnsemble(members).fit(va_b.text.tolist(), va_b.label.values)
    save(ens, "stacked_ensemble")
    oof = cross_val_predict(LogisticRegression(max_iter=1000),
                            np.column_stack([_logit(S["val"][n]) for n in ens.order]),
                            va_b.label.values, cv=5, method="predict_proba")[:, 1]
    for split in sets:
        S[split]["stacked_ensemble"] = ens.predict_proba(None, scores=S[split])

    thr = {n: best_f1_threshold(va_b.label.values, S["val"][n]) for n in members}
    thr["stacked_ensemble"] = best_f1_threshold(va_b.label.values, oof)

    rows = []
    for split in ("test", "ood"):
        y = sets[split].label.values
        for n, p in S[split].items():
            for mode, t in (("default@0.5", 0.5), ("val-tuned", thr[n])):
                rows.append({"model": n, "eval_set": split, "threshold_mode": mode, **binary_report(y, p, t)})
    # trained models are cheap: also report them on the full test split
    for n, m in (("tfidf_lr", tfidf), ("minilm_xgb", exgb)):
        rows.append({"model": n, "eval_set": "test_full", "threshold_mode": "val-tuned",
                     **binary_report(te.label.values, m.predict_proba(te.text.tolist()), thr[n])})
    res = pd.DataFrame(rows)
    res.to_csv(C.RESULTS_DIR / "text_metrics.csv", index=False)

    per_src = []
    for src, g in te_b.assign(_i=np.arange(len(te_b))).groupby("source"):
        for n, p in S["test"].items():
            r = binary_report(g.label.values, p[g._i.values], thr[n])
            per_src.append({"source": src, "model": n, "n": r["n"], "accuracy": r["accuracy"],
                            "f1": r["f1"], "fpr": r["fpr"]})
    pd.DataFrame(per_src).to_csv(C.RESULTS_DIR / "text_per_source.csv", index=False)

    json.dump({"thresholds": thr, "ensemble_weights": ens.weights()},
              open(C.MODELS_DIR / "text_thresholds.json", "w"), indent=2)

    names = list(S["test"])
    plots.roc_pr([(n, te_b.label.values, S["test"][n]) for n in names],
                 C.RESULTS_DIR / "text_roc_pr_test.png", "Layer 1 content detectors - in-distribution test")
    plots.roc_pr([(n, ood.label.values, S["ood"][n]) for n in names],
                 C.RESULTS_DIR / "text_roc_pr_ood.png", "Layer 1 content detectors - out-of-distribution test")
    tuned = res[res.threshold_mode == "val-tuned"]
    plots.grouped_bars(
        names, {f"F1 ({s})": [tuned[(tuned.model == n) & (tuned.eval_set == s)].f1.iloc[0] for n in names]
                for s in ("test", "ood")},
        C.RESULTS_DIR / "text_f1_bars.png", "Layer 1: F1 by model (val-tuned thresholds)", "F1")

    view = tuned[tuned.eval_set.isin(["test", "ood"])][
        ["eval_set", "model", "accuracy", "precision", "recall", "f1", "fpr", "roc_auc", "pr_auc"]]
    print(view.sort_values(["eval_set", "f1"], ascending=[True, False]).round(4).to_string(index=False))
    print("ensemble weights:", ens.weights())
    return res

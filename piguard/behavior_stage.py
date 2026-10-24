"""Stage 2: behavioural monitor - features, grouped cross-validation, ablations, final model."""
import json

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from . import config as C
from . import plots
from .behavior import BEHAVIOUR_ONLY, FEATURES, TEXT_ONLY, BehaviorMonitor, MemoScorer, trace_features
from .metrics import binary_report
from .text_detectors import Embedder, load_text_detector
from .traces import load_traces

FEATURES_PATH = C.DATA_PROC / "action_features.csv"
OOF_PATH = C.DATA_PROC / "action_oof.csv"


def _xgb():
    return XGBClassifier(n_estimators=400, max_depth=4, learning_rate=0.05, subsample=0.9,
                         colsample_bytree=0.8, tree_method="hist", n_jobs=-1, random_state=C.SEED,
                         eval_metric="logloss")


class RuleBaseline:
    """Block any non-first write/high-risk action after an observation flagged by Layer 1."""

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        p = ((X["obs_inj_max"] >= 0.5) & (X["risk_level"] >= 1) & (X["step"] > 0)).astype(float).values
        return np.column_stack([1 - p, p])


class IsoForest:
    """Unsupervised anomaly detector trained on benign actions only."""

    def fit(self, X, y):
        Xb = X[y == 0]
        self.sc = StandardScaler().fit(Xb)
        self.m = IsolationForest(n_estimators=300, contamination="auto", random_state=C.SEED).fit(self.sc.transform(Xb))
        s = -self.m.score_samples(self.sc.transform(Xb))
        self.lo, self.cut = np.percentile(s, 1), np.percentile(s, 97)  # 3% benign false-alarm budget
        return self

    def predict_proba(self, X):
        s = -self.m.score_samples(self.sc.transform(X))
        p = 1 / (1 + np.exp(-(s - self.cut) / max((self.cut - self.lo) / 6, 1e-6)))
        return np.column_stack([1 - p, p])


MODELS = {
    "rule_baseline (L1 flag + risky tool)": (["obs_inj_max", "risk_level", "step"], RuleBaseline),
    "text_only_lr (L1 scores)": (TEXT_ONLY + ["step"], lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))),
    "isolation_forest (unsupervised)": (FEATURES, IsoForest),
    "behaviour_only_xgb (no L1)": (BEHAVIOUR_ONLY, _xgb),
    "full_lr": (FEATURES, lambda: make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=3000))),
    "full_rf": (FEATURES, lambda: RandomForestClassifier(n_estimators=400, min_samples_leaf=2, n_jobs=-1, random_state=C.SEED)),
    "full_xgb (proposed)": (FEATURES, _xgb),
}
PROPOSED = "full_xgb (proposed)"


def build_features(obs_detector):
    traces = load_traces()
    det = load_text_detector(obs_detector)
    mon = BehaviorMonitor(MemoScorer(det.predict_proba), MemoScorer(Embedder.encode))
    prev = C.DATA_PROC / f"obs_segment_scores_{obs_detector}.json"
    if prev.exists():  # reuse transformer scores from earlier runs (scoring is the slow part on CPU)
        mon.score.memo.update(json.load(open(prev, encoding="utf8")))
    df = pd.DataFrame(trace_features(traces, mon))
    df.to_csv(FEATURES_PATH, index=False)
    scores = {k: float(v) for k, v in mon.score.memo.items()}
    for p in (prev, C.DATA_PROC / "obs_segment_scores.json"):
        json.dump(scores, open(p, "w", encoding="utf8"))
    return df


def grouped_oof(df, groups, name):
    cols, factory = MODELS[name]
    oof = np.zeros(len(df))
    for g in np.unique(groups):
        tr, te = groups != g, groups == g
        m = factory().fit(df.loc[tr, cols], df.label[tr].values)
        oof[te] = m.predict_proba(df.loc[te, cols])[:, 1]
    return oof


def run(obs_detector="stacked_ensemble"):
    print(f"[behaviour] extracting features (observation detector = {obs_detector})")
    df = build_features(obs_detector)
    print(df.groupby("scenario")[["goal_sim", "drift", "arg_from_obs_only", "obs_inj_max"]].mean().round(3).to_string())

    users = sorted(df.user_tool.unique())
    user_fold = df.user_tool.map({u: i % 5 for i, u in enumerate(users)}).values
    protocols = {"unseen_attacker_goals": df.fold.values, "unseen_user_tasks": user_fold}

    rows, scen_rows, oof_keep = [], [], {}
    for proto, groups in protocols.items():
        for name in MODELS:
            p = grouped_oof(df, groups, name)
            rows.append({"protocol": proto, "model": name, **binary_report(df.label.values, p, 0.5)})
            for scen, g in df.assign(p=p).groupby("scenario"):
                scen_rows.append({"protocol": proto, "model": name, "scenario": scen, "actions": len(g),
                                  "flag_rate_benign_actions": float((g.p[g.label == 0] >= 0.5).mean()) if (g.label == 0).any() else np.nan,
                                  "detection_rate_malicious": float((g.p[g.label == 1] >= 0.5).mean()) if (g.label == 1).any() else np.nan})
            oof_keep[(proto, name)] = p
            print(f"  {proto:22s} {name:38s} F1={rows[-1]['f1']:.4f} AUC={rows[-1]['roc_auc']:.4f} FPR={rows[-1]['fpr']:.4f}")

    res = pd.DataFrame(rows)
    res.to_csv(C.RESULTS_DIR / "behavior_metrics.csv", index=False)
    pd.DataFrame(scen_rows).to_csv(C.RESULTS_DIR / "behavior_per_scenario.csv", index=False)

    oof = df[["trace_id", "scenario", "variant", "fold", "tool", "label", "obs_inj_max", "step"]].copy()
    for name in MODELS:
        oof[name] = oof_keep[("unseen_attacker_goals", name)]
    oof.to_csv(OOF_PATH, index=False)

    # final deployable model on all traces
    final = _xgb().fit(df[FEATURES], df.label.values)
    joblib.dump({"model": final, "features": FEATURES, "threshold": 0.5, "obs_detector": obs_detector},
                C.MODELS_DIR / "behavior_xgb.joblib")
    imp = pd.Series(final.get_booster().get_score(importance_type="gain")).reindex(FEATURES).fillna(0)
    imp = (imp / imp.sum()).sort_values(ascending=False)
    imp.to_csv(C.RESULTS_DIR / "behavior_feature_importance.csv", header=["gain_share"])

    names = list(MODELS)
    plots.grouped_bars(
        [n.split(" (")[0] for n in names],
        {f"F1 - {p.replace('_', ' ')}": [res[(res.protocol == p) & (res.model == n)].f1.iloc[0] for n in names]
         for p in protocols},
        C.RESULTS_DIR / "behavior_f1_bars.png", "Layer 2: hijacked tool-call detection (grouped CV)", "F1")
    plots.grouped_bars(list(imp.index), {"gain share": list(imp.values)},
                       C.RESULTS_DIR / "behavior_feature_importance.png",
                       "Layer 2: XGBoost feature importance", "share of total gain", ylim=(0, max(imp.max() * 1.2, 0.1)))
    plots.roc_pr([(n.split(" (")[0], df.label.values, oof_keep[("unseen_attacker_goals", n)]) for n in names],
                 C.RESULTS_DIR / "behavior_roc_pr.png", "Layer 2 - unseen attacker goals")
    r = res[(res.protocol == "unseen_attacker_goals") & (res.model == PROPOSED)].iloc[0]
    cm = [[r.tn, r.fp], [r.fn, r.tp]]
    plots.confusion(cm, C.RESULTS_DIR / "behavior_confusion.png", "Proposed monitor (unseen goals)",
                    ("legit call", "hijacked call"))
    json.dump(imp.round(4).to_dict(), open(C.RESULTS_DIR / "behavior_feature_importance.json", "w"), indent=2)
    print(res[["protocol", "model", "accuracy", "precision", "recall", "f1", "fpr", "roc_auc"]].round(4).to_string(index=False))
    return res

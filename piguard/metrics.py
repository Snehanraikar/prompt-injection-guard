import numpy as np
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix, f1_score,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score)


def binary_report(y, p, thr=0.5):
    y = np.asarray(y)
    yhat = (np.asarray(p) >= thr).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, yhat, labels=[0, 1]).ravel()
    both = len(np.unique(y)) == 2
    return {
        "n": len(y), "threshold": round(float(thr), 4),
        "accuracy": accuracy_score(y, yhat),
        "precision": precision_score(y, yhat, zero_division=0),
        "recall": recall_score(y, yhat, zero_division=0),
        "f1": f1_score(y, yhat, zero_division=0),
        "fpr": fp / max(fp + tn, 1),
        "roc_auc": roc_auc_score(y, p) if both else np.nan,
        "pr_auc": average_precision_score(y, p) if both else np.nan,
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
    }


def best_f1_threshold(y, p):
    prec, rec, thr = precision_recall_curve(y, p)
    f1 = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
    return float(thr[np.argmax(f1[:-1])])

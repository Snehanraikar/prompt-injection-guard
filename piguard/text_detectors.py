"""Layer 1 - content detectors for injected instructions.

* HFDetector      : Kaggle-hosted benchmark transformers (ProtectAI DeBERTa-v3, Wolf Defender, Prompt Guard)
* TfidfDetector   : word+char TF-IDF -> logistic regression, trained on the Kaggle corpus
* EmbedXGBDetector: MiniLM sentence embeddings + lexical cues -> XGBoost
* StackedEnsemble : logistic-regression stacker over the above, fit on the validation split
"""
import hashlib
import os

import joblib
import numpy as np

from . import config as C
from .features import lexical_features

CACHE_DIR = C.DATA_PROC / "score_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cached(name, texts, fn):
    """Memoise fn(texts) -> np.ndarray on disk, keyed by the exact list of texts."""
    h = hashlib.md5("\x00".join(map(str, texts)).encode("utf8")).hexdigest()[:16]
    path = CACHE_DIR / f"{name}_{h}.npy"
    if path.exists():
        return np.load(path)
    out = np.asarray(fn(texts))
    np.save(path, out)
    return out


class HFDetector:
    BENIGN_NAMES = {"safe", "benign", "legit", "legitimate", "label_0", "normal"}

    def __init__(self, name, path, max_length=C.HF_MAX_LENGTH, batch_size=C.HF_BATCH_SIZE):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        torch.set_num_threads(os.cpu_count() or 4)
        self.name, self.max_length, self.batch_size = name, max_length, batch_size
        self.tok = AutoTokenizer.from_pretrained(path)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModelForSequenceClassification.from_pretrained(path).eval().to(self.device)
        labels = {int(k): v.lower() for k, v in self.model.config.id2label.items()}
        self.benign_idx = [i for i, l in labels.items() if l in self.BENIGN_NAMES] or [0]

    def _predict(self, texts):
        import torch

        texts = list(map(str, texts))
        order = np.argsort([len(t) for t in texts])  # length-sorted batches -> little padding
        out = np.zeros(len(texts), dtype=np.float32)
        with torch.inference_mode():
            for s in range(0, len(texts), self.batch_size):
                idx = order[s:s + self.batch_size]
                enc = self.tok([texts[i] for i in idx], truncation=True, max_length=self.max_length,
                               padding=True, return_tensors="pt").to(self.device)
                probs = self.model(**enc).logits.float().softmax(-1)
                out[idx] = (1 - probs[:, self.benign_idx].sum(-1)).cpu().numpy()
        return out

    def predict_proba(self, texts):
        return cached(self.name, list(texts), self._predict)


def load_benchmark_detectors(names=None):
    from .download import model_path

    dets = {}
    for name in names or C.KAGGLE_MODELS:
        p = model_path(name)
        if p:
            dets[name] = HFDetector(name, p)
    return dets


class Embedder:
    _model = None

    @classmethod
    def encode(cls, texts):
        def run(ts):
            if cls._model is None:
                from sentence_transformers import SentenceTransformer
                cls._model = SentenceTransformer(C.EMBED_MODEL, device="cpu")
            return cls._model.encode(ts, batch_size=64, normalize_embeddings=True,
                                     show_progress_bar=len(ts) > 2000).astype(np.float32)
        return cached("minilm_emb", list(map(str, texts)), run)


class TfidfDetector:
    name = "tfidf_lr"

    def fit(self, texts, y):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline, make_union

        vec = make_union(
            TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=150_000, sublinear_tf=True),
            TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3, max_features=300_000,
                            sublinear_tf=True),
        )
        self.pipe = make_pipeline(vec, LogisticRegression(C=8.0, max_iter=3000, class_weight="balanced"))
        self.pipe.fit(list(texts), y)
        return self

    def predict_proba(self, texts):
        return self.pipe.predict_proba(list(map(str, texts)))[:, 1]


class EmbedXGBDetector:
    name = "minilm_xgb"

    @staticmethod
    def _feats(texts):
        texts = list(map(str, texts))
        return np.hstack([Embedder.encode(texts), lexical_features(texts)])

    def fit(self, texts, y):
        from xgboost import XGBClassifier

        self.clf = XGBClassifier(n_estimators=600, max_depth=6, learning_rate=0.08, subsample=0.9,
                                 colsample_bytree=0.6, tree_method="hist", n_jobs=-1,
                                 random_state=C.SEED, eval_metric="logloss")
        self.clf.fit(self._feats(texts), y)
        return self

    def predict_proba(self, texts):
        return self.clf.predict_proba(self._feats(texts))[:, 1]


def _logit(p):
    p = np.clip(p, 1e-5, 1 - 1e-5)
    return np.log(p / (1 - p))


class StackedEnsemble:
    """Combines member scores with a logistic regression fit on held-out (validation) data."""
    name = "stacked_ensemble"

    def __init__(self, members):
        self.members = members  # dict name -> object with predict_proba(texts)

    def member_scores(self, texts):
        return {n: m.predict_proba(texts) for n, m in self.members.items()}

    def fit(self, texts, y):
        from sklearn.linear_model import LogisticRegression

        S = self.member_scores(texts)
        self.order = list(S)
        self.clf = LogisticRegression(C=1.0, max_iter=1000).fit(
            np.column_stack([_logit(S[n]) for n in self.order]), y)
        return self

    def predict_proba(self, texts, scores=None):
        S = scores or self.member_scores(texts)
        return self.clf.predict_proba(np.column_stack([_logit(S[n]) for n in self.order]))[:, 1]

    def __getstate__(self):  # members (incl. torch models) are re-attached at load time
        return {k: v for k, v in self.__dict__.items() if k != "members"}

    def weights(self):
        return dict(zip(self.order, self.clf.coef_[0].round(3)))


def save(obj, name):
    joblib.dump(obj, C.MODELS_DIR / f"{name}.joblib")


def load(name):
    return joblib.load(C.MODELS_DIR / f"{name}.joblib")


def load_text_detector(name="stacked_ensemble"):
    """Any Layer-1 detector by name: trained (joblib), Kaggle benchmark, or the stacked ensemble."""
    if name in C.KAGGLE_MODELS:
        return load_benchmark_detectors([name])[name]
    obj = load(name)
    if isinstance(obj, StackedEnsemble):
        bench = load_benchmark_detectors([n for n in obj.order if n in C.KAGGLE_MODELS])
        obj.members = {n: bench[n] if n in bench else load(n) for n in obj.order}
    return obj

"""Hand-crafted lexical cues of injected instructions (cheap, interpretable)."""
import re

import numpy as np

CUE_PATTERNS = {
    "ignore_prev": r"\b(ignore|disregard|forget|override|bypass)\b.{0,40}\b(previous|prior|above|earlier|all|your)\b.{0,20}\b(instruction|prompt|rule|direction|guideline)s?",
    "new_instr": r"\b(new|updated|following|real|actual)\s+(instruction|task|rule|objective)s?\b",
    "role_play": r"\b(you are now|act as|pretend (to be|you)|roleplay|role-play|from now on|you will now)\b",
    "jailbreak_kw": r"\b(DAN|do anything now|jailbreak|developer mode|unfiltered|uncensored|no restrictions|without (any )?restrictions)\b",
    "system_ref": r"\b(system prompt|system message|initial prompt|hidden prompt|your instructions|your rules)\b",
    "urgency": r"\b(IMPORTANT|URGENT|ATTENTION|NOTE TO (THE )?(AI|ASSISTANT)|MUST|immediately)\b",
    "fake_delim": r"(</?\s*(system|user|assistant|instruction|im_start|im_end)\s*>|\[/?INST\]|###\s*(system|instruction)|^-{3,}|={3,})",
    "exfil_verb": r"\b(send|email|forward|transfer|upload|post|share|leak|reveal|print|output)\b.{0,60}\b(password|key|token|secret|address|account|credential|data|history|details)\b",
    "imperative_ai": r"\b(assistant|AI|model|chatbot|bot|agent)\b.{0,15}\b(must|should|will|shall)\b",
    "german_ignore": r"\b(vergiss|ignoriere|ignorieren)\b",
}
_COMPILED = {k: re.compile(v, re.I | re.M) for k, v in CUE_PATTERNS.items()}
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_URL = re.compile(r"https?://\S+|www\.\S+")
_B64 = re.compile(r"\b[A-Za-z0-9+/]{30,}={0,2}")

LEXICAL_NAMES = list(CUE_PATTERNS) + [
    "log_len", "n_lines", "upper_ratio", "punct_ratio", "non_ascii_ratio",
    "n_email", "n_url", "has_b64", "you_ratio", "question",
]


def lexical_features(texts):
    rows = []
    for t in texts:
        t = str(t)
        n = max(len(t), 1)
        words = t.split()
        nw = max(len(words), 1)
        row = [1.0 if p.search(t) else 0.0 for p in _COMPILED.values()]
        row += [
            np.log1p(len(t)),
            t.count("\n") + 1,
            sum(c.isupper() for c in t) / n,
            sum(not c.isalnum() and not c.isspace() for c in t) / n,
            sum(ord(c) > 127 for c in t) / n,
            len(_EMAIL.findall(t)),
            len(_URL.findall(t)),
            1.0 if _B64.search(t) else 0.0,
            sum(w.lower().strip(".,!?") in ("you", "your", "you're") for w in words) / nw,
            1.0 if t.rstrip().endswith("?") else 0.0,
        ]
        rows.append(row)
    return np.asarray(rows, dtype=np.float32)

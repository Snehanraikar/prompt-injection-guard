"""Layer 3 - RuntimeGuard: runtime detection + prevention middleware for tool-using LLM agents.

    guard = RuntimeGuard.load()                    # trained Layer-1 + Layer-2 models
    guard.start(user_instruction)
    send_email = guard.wrap("GmailSendEmail", real_send_email)
    result = send_email(to=..., subject=..., body=...)   # blocked -> returns an error payload instead

Every proposed tool call goes through check_action() (behavioural monitor) BEFORE it executes.
Every tool output goes through check_observation() (content detector) BEFORE the LLM sees it;
segments that look like injected instructions are quarantined.
"""
import json
import time
from dataclasses import asdict, dataclass, field

import joblib
import pandas as pd

from . import config as C
from .alerts import AlertManager
from .behavior import BehaviorMonitor, MemoScorer, segments
from .text_detectors import Embedder, load_text_detector

QUARANTINE = "[REMOVED BY GUARD: suspected prompt injection in untrusted tool output]"


@dataclass
class Verdict:
    kind: str                 # "action" | "observation"
    tool: str
    allowed: bool
    score: float
    reasons: list = field(default_factory=list)
    features: dict = field(default_factory=dict)


class RuntimeGuard:
    def __init__(self, text_detector, behavior_bundle, obs_threshold=0.5, mode="prevent", alerts=None):
        assert mode in ("prevent", "detect")
        self.mode = mode
        self.alerts = alerts or AlertManager()
        self.obs_threshold = obs_threshold
        self.model = behavior_bundle["model"]
        self.features_order = behavior_bundle["features"]
        self.action_threshold = behavior_bundle.get("threshold", 0.5)
        self.monitor = BehaviorMonitor(MemoScorer(text_detector.predict_proba), MemoScorer(Embedder.encode))
        self.audit = []
        self.sanitize = True  # Layer 1 quarantine on/off (scores are still computed for Layer 2)
        self.block = True     # Layer 2 blocking on/off (risk is still computed and shown)

    @classmethod
    def load(cls, mode="prevent", alerts=None):
        bundle = joblib.load(C.MODELS_DIR / "behavior_xgb.joblib")
        name = bundle.get("obs_detector", "stacked_ensemble")
        thr = json.load(open(C.MODELS_DIR / "text_thresholds.json"))["thresholds"].get(name, 0.5)
        return cls(load_text_detector(name), bundle, obs_threshold=thr, mode=mode, alerts=alerts)

    def start(self, user_instruction):
        self.monitor.reset(user_instruction)
        self.alerts.new_session(user_instruction)
        self.audit.append({"t": time.time(), "event": "session_start", "user": user_instruction})

    # ---------------- observations (Layer 1) ----------------
    def check_observation(self, tool, content):
        content = str(content)
        score, worst = self.monitor.observe(tool, content)  # monitor keeps the raw text for provenance
        flagged = [s for s in segments(content) if float(self.monitor.score(s)) >= self.obs_threshold]
        sanitized = content
        if not self.sanitize:
            flagged = []
        if self.mode == "prevent":
            for s in flagged:
                sanitized = sanitized.replace(s, QUARANTINE)
        v = Verdict("observation", tool, allowed=not flagged, score=round(score, 4),
                    reasons=[f"injection-like segment: {s[:90]!r}" for s in flagged])
        self.audit.append({"t": time.time(), **asdict(v)})
        self.alerts.on_observation(tool, score, flagged, self.mode)
        return sanitized, v

    # ---------------- actions (Layer 2) ----------------
    def check_action(self, tool, args):
        f = self.monitor.features(tool, args)
        feats = {k: round(float(x), 3) for k, x in f.items()}
        if self.block and self.alerts.locked and f["risk_level"] >= 1 and self.mode == "prevent":
            self.alerts.on_lockdown_refusal(tool, args)
            v = Verdict("action", tool, allowed=False, score=1.0,
                        reasons=["session in security lockdown after earlier hijack alerts"], features=feats)
            self.audit.append({"t": time.time(), **asdict(v), "args": args})
            return v
        p = float(self.model.predict_proba(pd.DataFrame([f])[self.features_order])[0, 1])
        blocked = p >= self.action_threshold and self.block
        v = Verdict("action", tool, allowed=not (blocked and self.mode == "prevent"), score=round(p, 4),
                    reasons=self.explain(f) if blocked else [], features=feats)
        if v.allowed:
            self.monitor.record_action(tool, args)
        self.audit.append({"t": time.time(), **asdict(v), "args": args})
        if blocked:
            self.alerts.on_action(tool, args, p, v.reasons, feats, blocked=self.mode == "prevent", mode=self.mode)
        return v

    @staticmethod
    def explain(f):
        r = []
        if f["arg_from_obs_only"] > 0.2:
            r.append(f"{f['arg_from_obs_only']:.0%} of argument values come from untrusted tool output, not the user")
        if f["new_contact"]:
            r.append("sends to a recipient/account the user never mentioned")
        if f["drift"] > 0:
            r.append(f"action matches untrusted content (sim {f['obs_sim']:.2f}) more than the user goal (sim {f['goal_sim']:.2f})")
        if f["obs_inj_max"] >= 0.5:
            r.append(f"a prior tool output was flagged as injection (score {f['obs_inj_max']:.2f})")
        if f["risk_level"] == 2 and not f["toolkit_in_goal"]:
            r.append("high-risk tool from a toolkit unrelated to the user request")
        if f["exfil_flow"] > 0.2:
            r.append("outbound action carrying values that were read from earlier tool outputs")
        return r or ["behavioural profile resembles hijacked tool calls"]

    # ---------------- integration ----------------
    def wrap(self, tool_name, fn):
        def guarded(**kwargs):
            v = self.check_action(tool_name, kwargs)
            if not v.allowed:
                return {"error": "Action blocked by security guard (possible prompt injection).",
                        "reasons": v.reasons}
            out = fn(**kwargs)
            sanitized, _ = self.check_observation(tool_name, out)
            return sanitized
        guarded.__name__ = tool_name
        return guarded

    def save_audit(self, path):
        with open(path, "w", encoding="utf8") as fh:
            for e in self.audit:
                fh.write(json.dumps(e, default=str) + "\n")

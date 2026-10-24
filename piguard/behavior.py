"""Layer 2 - behavioural monitor.

For every tool call an agent proposes, BehaviorMonitor computes features that describe *how the
action relates to the session*, using only information available at that moment:

  goal alignment     goal_sim, name_overlap, toolkit_in_goal
  drift / influence  obs_sim, sim_suspicious, drift (= obs_sim - goal_sim), susp_overlap
  provenance (taint) arg_from_user, arg_from_obs_only, new_contact
  capability / risk  risk_level, outbound, exfil_flow, new_toolkit
  context            obs_inj_max, obs_inj_last (Layer-1 scores of untrusted tool outputs), step
"""
import ast
import json
import re

import numpy as np

from .traces import load_tool_catalog

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
URL = re.compile(r"https?://\S+|www\.\S+")
CONTACTISH = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|https?://\S+|\+?\d[\d -]{6,}\d|\b\d{3}-\d{4}-\d{4}\b")
WORD = re.compile(r"[a-z0-9_.@+-]{3,}")
STOP = set("the and for with from that this your you are was were have has had into about please can could "
           "would should will what which when where who how all any also then them they their there our "
           "my me its not but just more most some such than too very via per".split())

HIGH = {"send", "transfer", "pay", "withdraw", "deposit", "grant", "unlock", "delete", "remove", "execute",
        "share", "post", "publish", "forward", "upload", "invite", "revoke", "disable", "purchase", "buy",
        "sell", "place", "order", "dispatch", "trade", "move", "manage", "create", "update", "modify",
        "reply", "add", "book", "cancel", "set", "control", "change", "schedule", "make", "redirect"}
OUTBOUND = {"send", "share", "post", "publish", "forward", "upload", "reply", "transfer", "invite"}
READ = {"get", "search", "view", "read", "list", "fetch", "retrieve", "check", "find", "download", "query",
        "lookup", "show", "track"}

FEATURES = ["goal_sim", "obs_sim", "sim_suspicious", "drift", "name_overlap", "toolkit_in_goal",
            "susp_overlap", "arg_from_user", "arg_from_obs_only", "n_atoms", "new_contact", "risk_level",
            "outbound", "exfil_flow", "new_toolkit", "obs_inj_max", "obs_inj_last", "step"]
TEXT_ONLY = ["obs_inj_max", "obs_inj_last"]
BEHAVIOUR_ONLY = [f for f in FEATURES if f not in TEXT_ONLY]


def camel_tokens(name):
    return [w.lower() for w in re.findall(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+", name)]


def _stem(w):
    return w[:-1] if w.endswith("s") and len(w) > 4 else w


def words(text):
    return {_stem(w.strip(".,@-_+")) for w in WORD.findall(str(text).lower())} - STOP


def flatten_values(x):
    if isinstance(x, dict):
        return [v for val in x.values() for v in flatten_values(val)]
    if isinstance(x, (list, tuple)):
        return [v for val in x for v in flatten_values(val)]
    return [str(x)]


def segments(content):
    """String leaves of a structured tool output (the places an injection can hide)."""
    s = str(content).strip()
    obj = None
    for parse in (json.loads, ast.literal_eval):
        try:
            obj = parse(s)
            break
        except Exception:
            continue
    if isinstance(obj, (dict, list)):
        segs = [v.strip() for v in flatten_values(obj)]
    else:
        segs = [p.strip() for p in re.split(r"\n{2,}|(?<=[.!?])\s+(?=[A-Z])", s)]
    # only natural-language text (>= MIN_WORDS words) can carry an instruction; ids, flags and
    # short labels are left to the behavioural layer. May return [] (nothing textual to scan).
    return [p[:2000] for p in segs if len(p.split()) >= MIN_WORDS][:50]


MIN_WORDS = 4


class MemoScorer:
    """Wrap a batch function texts -> array with a memo; prime() fills it in one batch."""

    def __init__(self, fn):
        self.fn, self.memo = fn, {}

    def prime(self, texts):
        new = list(dict.fromkeys(t for t in texts if t not in self.memo))
        if new:
            for t, v in zip(new, self.fn(new)):
                self.memo[t] = v

    def __call__(self, text):
        if text not in self.memo:
            self.prime([text])
        return self.memo[text]


class BehaviorMonitor:
    def __init__(self, obs_scorer, embedder, catalog=None):
        """obs_scorer: MemoScorer(texts -> P(injection)); embedder: MemoScorer(texts -> unit vectors)."""
        self.score, self.embed = obs_scorer, embedder
        self.catalog = catalog if catalog is not None else load_tool_catalog()

    # ---- session state -------------------------------------------------
    def reset(self, user_instruction):
        self.goal = user_instruction
        self.goal_words = words(user_instruction)
        self.goal_lower = user_instruction.lower()
        self.obs = []  # dicts: segs, scores, text, from_read
        self.actions = []
        self.toolkits_used = set()

    def tool_text(self, tool, args):
        info = self.catalog.get(tool, {})
        vals = " ".join(flatten_values(args))[:400]
        return f"{' '.join(camel_tokens(tool))}. {info.get('summary', '')} {vals}".strip()

    def observe(self, tool, content):
        segs = segments(content)
        scores = np.array([float(self.score(s)) for s in segs])
        verbs = set(camel_tokens(tool))
        self.obs.append({"segs": segs, "scores": scores, "text": str(content).lower(),
                         "from_read": bool(verbs & READ) and not bool(verbs & HIGH)})
        if not segs:
            return 0.0, ""
        return float(scores.max()), segs[int(scores.argmax())]

    def record_action(self, tool, args):
        self.actions.append((tool, args))
        self.toolkits_used.add(self.catalog.get(tool, {}).get("toolkit", tool))

    # ---- features for a proposed action --------------------------------
    def features(self, tool, args):
        atext = self.tool_text(tool, args)
        a_emb = self.embed(atext)
        goal_sim = float(a_emb @ self.embed(self.goal))
        name_toks = {_stem(t) for t in camel_tokens(tool)} - STOP
        toolkit = self.catalog.get(tool, {}).get("toolkit", tool)
        tk_toks = {_stem(t) for t in camel_tokens(toolkit)}
        verbs = set(camel_tokens(tool))
        risk = 2 if verbs & HIGH else (0 if verbs & READ else 1)
        outbound = int(bool(verbs & OUTBOUND))

        vals = flatten_values(args)
        atoms = set()
        for v in vals:
            atoms |= {m.lower() for m in CONTACTISH.findall(v)}
            atoms |= words(v) if len(v) < 300 else set()
        obs_text = " ".join(o["text"] for o in self.obs)
        in_user = [a for a in atoms if a in self.goal_lower]
        in_obs_only = [a for a in atoms if a not in self.goal_lower and a in obs_text]
        contacts = {m.lower() for v in vals for m in CONTACTISH.findall(v)}
        new_contact = int(any(c not in self.goal_lower for c in contacts))
        read_text = " ".join(o["text"] for o in self.obs if o["from_read"])
        exfil = outbound * (sum(a in read_text for a in atoms) / max(len(atoms), 1))

        all_segs = [s for o in self.obs for s in o["segs"]]
        if all_segs:
            all_scores = np.concatenate([o["scores"] for o in self.obs])
            sims = np.array([float(a_emb @ self.embed(s)) for s in all_segs])
            susp = int(all_scores.argmax())
            obs_sim, sim_susp = float(sims.max()), float(sims[susp])
            susp_overlap = len(words(atext) & words(all_segs[susp])) / max(len(words(atext)), 1)
            last = self.obs[-1]["scores"]
            inj_max, inj_last = float(all_scores.max()), float(last.max()) if len(last) else 0.0
        else:
            obs_sim = sim_susp = susp_overlap = inj_max = inj_last = 0.0

        return {
            "goal_sim": goal_sim, "obs_sim": obs_sim, "sim_suspicious": sim_susp, "drift": obs_sim - goal_sim,
            "name_overlap": len(name_toks & self.goal_words) / max(len(name_toks), 1),
            "toolkit_in_goal": int(bool(tk_toks & self.goal_words)),
            "susp_overlap": susp_overlap,
            "arg_from_user": len(in_user) / max(len(atoms), 1),
            "arg_from_obs_only": len(in_obs_only) / max(len(atoms), 1),
            "n_atoms": len(atoms), "new_contact": new_contact, "risk_level": risk, "outbound": outbound,
            "exfil_flow": exfil, "new_toolkit": int(toolkit not in self.toolkits_used and not tk_toks & self.goal_words),
            "obs_inj_max": inj_max, "obs_inj_last": inj_last, "step": len(self.actions),
        }


def trace_features(traces, monitor):
    """Replay traces through the monitor -> one feature row per proposed action."""
    texts = []
    for t in traces:  # batch-prime scorers so replay is fast
        for e in t["events"]:
            if e["role"] == "observation":
                texts += segments(e["content"])
    monitor.score.prime(texts)
    emb_texts = list(texts)
    for t in traces:
        emb_texts.append(t["events"][0]["content"])
        emb_texts += [monitor.tool_text(e["tool"], e["args"]) for e in t["events"] if e["role"] == "action"]
    monitor.embed.prime(emb_texts)

    rows = []
    for t in traces:
        monitor.reset(t["events"][0]["content"])
        for e in t["events"][1:]:
            if e["role"] == "action":
                f = monitor.features(e["tool"], e["args"])
                rows.append({"trace_id": t["trace_id"], "scenario": t["scenario"], "variant": t["variant"],
                             "fold": t["fold"], "user_tool": t["user_tool"], "tool": e["tool"],
                             "label": e["label"], **f})
                monitor.record_action(e["tool"], e["args"])
            elif e["role"] == "observation":
                monitor.observe(e["tool"], e["content"])
    return rows

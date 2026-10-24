"""Build tool-using agent traces from the InjecAgent benchmark.

Every (user case u, attacker case a) pair yields:
  A  benign                 user task, clean tool output, no extra actions
  B  injected_resisted      tool output carries the injection, agent ignores it
  C  injected_hijacked      agent follows the injection -> attacker tool calls   (actions label 1)
  D  benign_sensitive       the USER asks for the same sensitive actions -> identical tools, authorised
  E  injected_legit_mix     injection present AND the user asked for a different sensitive task
B, C, E come in InjecAgent's "base" and "enhanced" (IMPORTANT!!! Ignore all previous...) variants.
D and E are hard negatives: the monitor must reason about provenance, not tool type.

Attacker cases are split into 5 folds (E pairs cases within a fold) so evaluation can hold out
entire attacker goals.
"""
import ast
import json
import random
import re

import pandas as pd

from . import config as C
from .data import load_corpus

TRACES_PATH = C.DATA_PROC / "traces.jsonl"
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
NUMBER = re.compile(r"\$?\d[\d,]*(?:\.\d+)?")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?")
IDLIKE = re.compile(r"\b(?=[\w-]*\d)[A-Za-z0-9][\w-]{3,}\b|\b\w+_\w+\b")
FREE_TEXT = {"content", "body", "message", "text", "description", "comment", "note", "query",
             "keywords", "title", "subject", "reason", "instructions", "command"}


def load_tool_catalog():
    cat = {}
    for tk in json.load(open(C.INJECAGENT_DIR / "tools.json", encoding="utf8")):
        for t in tk["tools"]:
            cat[tk["toolkit"] + t["name"]] = {
                "toolkit": tk["toolkit"], "summary": t.get("summary", ""),
                "params": t.get("parameters", []),
            }
    return cat


def _jsonl(name):
    return [json.loads(l) for l in open(C.INJECAGENT_DIR / name, encoding="utf8")]


def _sim_responses():
    """attacker_simulated_responses keys look like '(Tool,{json args})' -> first args/response per tool."""
    raw = json.load(open(C.INJECAGENT_DIR / "attacker_simulated_responses.json", encoding="utf8"))
    out = {}
    for k, v in raw.items():
        tool, args = k[1:-1].split(",", 1)
        if tool not in out:
            try:
                out[tool] = (json.loads(args), v)
            except json.JSONDecodeError:
                continue
    return out


def derive_args(tool, instruction, catalog):
    """Fill a tool's parameters from entities in the (attacker or user) instruction."""
    text = re.sub(r"^(IMPORTANT!!!.*?instruction:\s*)", "", instruction)
    emails, dates = EMAIL.findall(text), DATE.findall(text)
    no_email = EMAIL.sub(" ", text)
    ids = [m for m in IDLIKE.findall(no_email) if not DATE.fullmatch(m)]
    nums = [n.replace("$", "").replace(",", "") for n in NUMBER.findall(DATE.sub(" ", no_email))]
    body = re.sub(r"^please\s+", "", text.strip(), flags=re.I)
    args = {}
    for p in catalog.get(tool, {}).get("params", []):
        name, typ = p["name"].lower(), p.get("type", "string")
        val = None
        if ("email" in name or name in ("to", "recipient", "recipients", "cc")) and emails:
            val = ", ".join(emails)
        elif typ == "boolean":
            val = True
        elif ("date" in name or "time" in name) and dates:
            val = dates[0]
        elif typ in ("number", "integer") or any(k in name for k in ("amount", "price", "quantity")):
            val = float(nums[0]) if nums else None
        elif any(k in name for k in ("id", "number", "account", "payee", "code")) and ids:
            val = ids if typ == "array" else ids[0]
        elif name in FREE_TEXT or any(k in name for k in FREE_TEXT):
            val = body
        if val is None and p.get("required"):
            val = ids[0] if ids else body[:80]
        if val is not None:
            args[p["name"]] = val
    return args


def _attacker_actions(case, instruction, catalog, sim):
    """Tool calls an agent makes to accomplish `case` (data-stealing cases read, then email)."""
    steps = []
    tools = case["Attacker Tools"]
    if len(tools) == 2:  # data stealing: read private data -> GmailSendEmail to attacker
        args, resp = sim.get(tools[0], (derive_args(tools[0], instruction, catalog), {"result": "ok"}))
        obs = json.dumps(resp)[:1500]
        steps.append(({"tool": tools[0], "args": args}, obs))
        to = ", ".join(EMAIL.findall(instruction)) or "amy.watson@gmail.com"
        steps.append(({"tool": tools[1], "args": {
            "to": to, "subject": f"{catalog.get(tools[0], {}).get('toolkit', 'Account')} information",
            "body": obs[:400]}}, json.dumps({"success": True})))
    else:
        for t in tools:
            steps.append(({"tool": t, "args": derive_args(t, instruction, catalog)},
                          json.dumps({"success": True})))
    return steps


def _fill(template, text):
    return template.replace("<Attacker Instruction>", text.replace("'", "’"))


def build_traces(seed=C.SEED):
    rng = random.Random(seed)
    catalog, sim = load_tool_catalog(), _sim_responses()
    users = _jsonl("user_cases.jsonl")
    attackers = _jsonl("attacker_cases_dh.jsonl") + _jsonl("attacker_cases_ds.jsonl")
    for i, a in enumerate(attackers):
        a["id"] = f"{'dh' if len(a['Attacker Tools']) == 1 else 'ds'}{i:02d}"
    order = list(range(len(attackers)))
    rng.shuffle(order)
    fold_of = {attackers[i]["id"]: k % 5 for k, i in enumerate(order)}
    by_fold = {f: [a for a in attackers if fold_of[a["id"]] == f] for f in range(5)}

    # Injected tool responses exactly as in InjecAgent (base / enhanced)
    injected = {}
    for v in ("base", "enhanced"):
        for kind in ("dh", "ds"):
            for tc in json.load(open(C.INJECAGENT_DIR / f"test_cases_{kind}_{v}.json", encoding="utf8")):
                injected[(tc["User Instruction"], tc["Attacker Instruction"], v)] = tc["Tool Response"].strip('"')

    # Benign filler for tool outputs: benign texts the Layer-1 models never trained on
    corpus = load_corpus()
    fill = corpus[(corpus.split == "test") & (corpus.label == 0) & corpus.text.str.len().between(25, 220)]
    fillers = fill.text.sample(frac=1, random_state=seed).tolist()

    traces, tid = [], 0

    def emit(scenario, variant, u, a_inj, a_legit, user_text, first_obs, follow):
        nonlocal tid
        ev = [{"role": "user", "content": user_text},
              {"role": "action", "tool": u["User Tool"], "args": ast.literal_eval(u["Tool Parameters"]),
               "label": 0},
              {"role": "observation", "tool": u["User Tool"], "content": first_obs}]
        for act, obs, lab in follow:
            ev.append({"role": "action", **act, "label": lab})
            ev.append({"role": "observation", "tool": act["tool"], "content": obs})
        ev.append({"role": "final", "content": "Done - here is a summary of the results."})
        primary = a_inj or a_legit
        traces.append({
            "trace_id": tid, "scenario": scenario, "variant": variant, "user_tool": u["User Tool"],
            "attacker_case": a_inj["id"] if a_inj else None, "legit_case": a_legit["id"] if a_legit else None,
            "attack_type": primary["Attack Type"], "fold": fold_of[primary["id"]],
            "hijacked": int(any(e.get("label") == 1 for e in ev)), "events": ev})
        tid += 1

    for u in users:
        for a in attackers:
            filler = fillers[tid % len(fillers)]
            clean_obs = _fill(u["Tool Response Template"], filler)
            emit("benign", "-", u, None, a, u["User Instruction"], clean_obs, [])
            legit_text = f"{u['User Instruction']} Also, {a['Attacker Instruction'][0].lower()}{a['Attacker Instruction'][1:]}"
            emit("benign_sensitive", "-", u, None, a, legit_text, clean_obs,
                 [(act, obs, 0) for act, obs in _attacker_actions(a, a["Attacker Instruction"], catalog, sim)])
            partner = rng.choice([b for b in by_fold[fold_of[a["id"]]] if b["id"] != a["id"]])
            for v in ("base", "enhanced"):
                inj_obs = injected[(u["User Instruction"], a["Attacker Instruction"], v)]
                emit("injected_resisted", v, u, a, None, u["User Instruction"], inj_obs, [])
                emit("injected_hijacked", v, u, a, None, u["User Instruction"], inj_obs,
                     [(act, obs, 1) for act, obs in _attacker_actions(a, a["Attacker Instruction"], catalog, sim)])
                mix_text = f"{u['User Instruction']} Also, {partner['Attacker Instruction'][0].lower()}{partner['Attacker Instruction'][1:]}"
                emit("injected_legit_mix", v, u, a, partner, mix_text, inj_obs,
                     [(act, obs, 0) for act, obs in _attacker_actions(partner, partner["Attacker Instruction"], catalog, sim)])

    with open(TRACES_PATH, "w", encoding="utf8") as f:
        for t in traces:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    df = pd.DataFrame(traces)
    n_act = df.events.map(lambda ev: sum(e["role"] == "action" for e in ev))
    n_mal = df.events.map(lambda ev: sum(e.get("label") == 1 for e in ev))
    print(df.assign(actions=n_act, malicious_actions=n_mal)
            .groupby("scenario")[["trace_id", "actions", "malicious_actions"]]
            .agg({"trace_id": "count", "actions": "sum", "malicious_actions": "sum"})
            .rename(columns={"trace_id": "traces"}).to_string())
    return traces


def load_traces():
    if not TRACES_PATH.exists():
        return build_traces()
    return [json.loads(l) for l in open(TRACES_PATH, encoding="utf8")]

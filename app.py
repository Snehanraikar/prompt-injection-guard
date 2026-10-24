"""Live demo dashboard (started in the cloud by cloud/start.sh, or locally: streamlit run app.py)."""
import json
import random
import time
import warnings

warnings.filterwarnings("ignore")

import joblib
import pandas as pd
import streamlit as st

from piguard import config as C
from piguard.alerts import AlertManager
from piguard.live_agent import ATTACKER_ACCOUNT, ATTACKER_EMAIL, SCENARIOS, World, ollama_available, run_llm, run_scripted

st.set_page_config(page_title="Prompt-Injection Runtime Guard", page_icon="🛡️", layout="wide")
R = C.RESULTS_DIR
SEV = {"MEDIUM": "🟠", "HIGH": "🔴", "CRITICAL": "⛔"}
CHANNEL = {"email": "📧 email", "review": "🛒 product review", "calendar": "📅 calendar event"}

st.markdown("""<style>
.block-container {padding-top: 1.6rem;}
.badge {display:inline-block;padding:2px 10px;border-radius:12px;font-weight:600;font-size:0.85rem;}
.ok {background:#e3f4ea;color:#0b6b2e;} .bad {background:#fde4e4;color:#a11d1d;} .warn {background:#fff1d6;color:#8a5a00;}
.call {font-family:monospace;font-size:0.9rem;}
.big-outcome {font-size:1.35rem;font-weight:700;padding:14px 18px;border-radius:10px;margin-top:6px;}
</style>""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Loading detectors (Kaggle benchmark models + trained models) ...")
def get_guard():
    from piguard.guard import RuntimeGuard
    g = RuntimeGuard.load(mode="prevent", alerts=AlertManager(console=False))
    p = C.DATA_PROC / "obs_segment_scores.json"
    if p.exists():
        g.monitor.score.memo.update(json.load(open(p, encoding="utf8")))
    return g


@st.cache_resource(show_spinner="Preparing held-out traffic (attacker goals the model never saw) ...")
def get_traffic():
    """Guard whose behaviour model was trained WITHOUT fold 4; traffic = fold-4 traces (unseen attacker goals)."""
    from piguard.behavior import FEATURES
    from piguard.behavior_stage import _xgb
    from piguard.guard import RuntimeGuard
    from piguard.traces import load_traces
    df = pd.read_csv(C.DATA_PROC / "action_features.csv")
    tr = df[df.fold != 4]
    bundle = {"model": _xgb().fit(tr[FEATURES], tr.label.values), "features": FEATURES, "threshold": 0.5}
    base = get_guard()
    g = RuntimeGuard(base.monitor.score.fn.__self__, bundle, obs_threshold=base.obs_threshold,
                     alerts=AlertManager(console=False, log_path=C.RESULTS_DIR / "traffic_alerts.jsonl"))
    g.monitor.score.memo = base.monitor.score.memo
    g.monitor.embed.memo = base.monitor.embed.memo
    traces = [t for t in load_traces() if t["fold"] == 4]
    return g, traces


page = st.sidebar.radio("Page", ["🎯 Live Attack Demo", "📡 Live Traffic Monitor", "📊 Results"], label_visibility="collapsed")

# =============================================================================================
if page.startswith("🎯"):
    st.title("🎯 Live Attack Demo")
    has_llm = ollama_available()
    with st.sidebar:
        st.subheader("Agent")
        brain = st.radio("brain", ["🤖 Real LLM (qwen2.5:3b, local)", "⚡ Fast replay"], index=0 if has_llm else 1,
                         label_visibility="collapsed", disabled=not has_llm)
        if not has_llm:
            st.caption("Ollama not running → fast replay")
        st.subheader("Protection")
        l1 = st.toggle("🛡️ Layer 1 · quarantine injected text", value=True)
        l2 = st.toggle("🛡️ Layer 2 · block hijacked actions", value=True)

    name = st.pills("Scenario", list(SCENARIOS), default=list(SCENARIOS)[0], label_visibility="collapsed") or list(SCENARIOS)[0]
    sc = dict(SCENARIOS[name])
    c1, c2 = st.columns([2, 3])
    sc["user"] = c1.text_area("👤 User asks the agent", sc["user"], height=110, key=f"u-{name}")
    sc["content"] = c2.text_area(f"☠️ Untrusted {CHANNEL[sc['channel']]} (attacker can write here)", sc["content"],
                                 height=110, key=f"c-{name}")
    go = st.button("▶  Run agent", type="primary", use_container_width=True)

    left, right = st.columns([3, 2])
    world = World(sc)
    with right:
        st.markdown("##### 🌍 User's world")
        wbox = st.empty()
        st.markdown("##### 🚨 Security alerts")
        abox = st.container()

    def show_world(w):
        with wbox.container():
            a, b = st.columns(2)
            a.metric("🏦 Bank balance", f"${w.balance:,.0f}", f"-${12_500 - w.balance:,.0f}" if w.balance < 12_500 else None)
            b.metric("🚪 Front door", "🔒 Locked" if w.door_locked else "🔓 UNLOCKED")
            a.metric("📤 Emails sent", len(w.sent))
            b.metric("🏠 Addresses", "🔴 LEAKED" if w.leaked else "🟢 Private")

    show_world(world)
    if go:
        guard = None
        if l1 or l2:
            guard = get_guard()
            guard.sanitize, guard.block = l1, l2
        runner = run_llm if brain.startswith("🤖") else run_scripted
        n_alerts, intervened = 0, False
        with left:
            st.markdown(f"##### 🤖 Agent timeline · protection: {'L1 ' if l1 else ''}{'L2' if l2 else ''}{'OFF' if not (l1 or l2) else ''}")
            status = None
            for ev in runner(sc, guard, world):
                if ev["type"] == "thinking":
                    status = st.status("Agent is thinking…", expanded=False)
                    continue
                if status is not None:
                    status.update(label="Agent decided", state="complete")
                    status = None
                if ev["type"] == "call":
                    v = ev["verdict"]
                    with st.container(border=True):
                        st.markdown(f"**➡️ Tool call** <span class='call'>{ev['tool']}({json.dumps(ev['args'])[:160]})</span>",
                                    unsafe_allow_html=True)
                        if v is None:
                            st.markdown("<span class='badge warn'>NO PROTECTION · executed</span>", unsafe_allow_html=True)
                        else:
                            st.progress(min(max(v.score, 0.0), 1.0), text=f"hijack risk {v.score:.2f}")
                            if v.allowed:
                                st.markdown("<span class='badge ok'>✅ ALLOWED</span>", unsafe_allow_html=True)
                            else:
                                intervened = True
                                st.markdown("<span class='badge bad'>🛑 BLOCKED</span>", unsafe_allow_html=True)
                                for r in v.reasons[:4]:
                                    st.caption(f"• {r}")
                elif ev["type"] == "output":
                    ov = ev["verdict"]
                    flagged = ov is not None and not ov.allowed
                    intervened |= flagged
                    with st.expander(("🧹 tool output - injection QUARANTINED" if flagged else "📄 tool output")
                                     + (f" · injection score {ov.score:.2f}" if ov is not None else ""), expanded=flagged):
                        st.code(ev["shown"][:700], language="json", wrap_lines=True)
                    show_world(world)
                elif ev["type"] == "alert":
                    a = ev["alert"]
                    n_alerts += 1
                    st.toast(f"{SEV[a.severity]} {a.severity}: {a.message}", icon="🚨")
                    with abox:
                        st.markdown(f"{SEV[a.severity]} **{a.severity}** · {a.category.replace('_', ' ')}  \n"
                                    f"<small>{a.message} → *{a.action_taken}*</small>", unsafe_allow_html=True)
                elif ev["type"] == "final":
                    with st.chat_message("assistant"):
                        st.write(ev["text"] or "(no answer)")
            show_world(world)
            stolen = any(t["to"] == ATTACKER_ACCOUNT for t in world.transfers) and not name.startswith("💸")
            harmed = stolen or not world.door_locked or world.leaked or any(ATTACKER_EMAIL in s["to"] for s in world.sent)
            attack = name[0] in "📧🛒🏠"
            if harmed:
                st.markdown("<div class='big-outcome bad'>💥 ATTACK SUCCEEDED - the agent was hijacked</div>", unsafe_allow_html=True)
            elif attack and intervened:
                st.markdown("<div class='big-outcome ok'>🛡️ ATTACK STOPPED BY THE GUARD - user's world unchanged</div>", unsafe_allow_html=True)
            elif attack:
                st.markdown("<div class='big-outcome warn'>🙂 The LLM ignored the injection this time - no harm "
                            "(switch to ⚡ Fast replay to show a hijacked agent)</div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='big-outcome ok'>✅ TASK COMPLETED - no interference</div>", unsafe_allow_html=True)
        if n_alerts == 0:
            with abox:
                st.caption("no alerts")
        if guard is not None and guard.alerts.locked:
            with abox:
                st.error("⛔ SESSION LOCKDOWN - human review required")

# =============================================================================================
elif page.startswith("📡"):
    st.title("📡 Live Traffic Monitor")
    st.caption("InjecAgent benchmark traffic · attacker goals never seen by this model")
    c1, c2, c3 = st.columns([2, 2, 1])
    n = c1.slider("Agent sessions", 20, 400, 120, step=20)
    speed = c2.select_slider("Speed", ["slow", "normal", "fast", "max"], value="normal")
    start = c3.button("▶ Start", type="primary", use_container_width=True)
    k = st.columns(4)
    kpi = [k[i].empty() for i in range(4)]
    chart_col, feed_col = st.columns([3, 2])
    chart = chart_col.empty()
    current = chart_col.empty()
    feed = feed_col.empty()

    def render_kpis(s):
        kpi[0].metric("Sessions", s["n"])
        kpi[1].metric("Attacks stopped", f"{s['stopped']}/{s['attacks']}",
                      f"{s['stopped'] / s['attacks']:.1%}" if s["attacks"] else None)
        kpi[2].metric("Legit tasks completed", f"{s['ok']}/{s['benign']}",
                      f"{s['ok'] / s['benign']:.1%}" if s["benign"] else None)
        kpi[3].metric("Security alerts", s["alerts"])

    stats = {"n": 0, "attacks": 0, "stopped": 0, "benign": 0, "ok": 0, "alerts": 0}
    render_kpis(stats)
    if start:
        guard, traces = get_traffic()
        guard.sanitize, guard.block = False, True  # replayed traces: measure the behavioural layer
        pool = random.Random(int(time.time())).sample(traces, min(n, len(traces)))
        delay = {"slow": 0.6, "normal": 0.25, "fast": 0.08, "max": 0.0}[speed]
        history, alerts = [], []
        for t in pool:
            guard.start(t["events"][0]["content"])
            blocked_mal, blocked_legit, last_call = False, False, None
            for e in t["events"][1:]:
                if e["role"] == "observation":
                    guard.check_observation(e["tool"], e["content"])
                elif e["role"] == "action":
                    v = guard.check_action(e["tool"], e["args"] if isinstance(e["args"], dict) else {"input": e["args"]})
                    last_call = (e["tool"], v)
                    if not v.allowed:
                        blocked_mal |= e["label"] == 1
                        blocked_legit |= e["label"] == 0
                        break
            stats["n"] += 1
            if t["hijacked"]:
                stats["attacks"] += 1
                stats["stopped"] += blocked_mal
            else:
                stats["benign"] += 1
                stats["ok"] += not blocked_legit
            new = guard.alerts.session_alerts
            stats["alerts"] += len(new)
            alerts = [(a.severity, a.tool, t["scenario"]) for a in new][::-1] + alerts
            history.append({"session": stats["n"],
                            "attack prevention %": 100 * stats["stopped"] / max(stats["attacks"], 1),
                            "legit tasks completed %": 100 * stats["ok"] / max(stats["benign"], 1)})
            render_kpis(stats)
            chart.line_chart(pd.DataFrame(history).set_index("session"), y_label="%", height=260)
            tool, v = last_call if last_call else ("-", None)
            verdict = "🛑 BLOCKED" if v is not None and not v.allowed else "✅ allowed"
            current.markdown(f"**👤** {t['events'][0]['content'][:140]}  \n**➡️** `{tool}` · risk {v.score if v else 0:.2f} · {verdict}"
                             f" · truth: {'☠️ hijacked' if t['hijacked'] else '🙂 legitimate'}")
            with feed.container():
                st.markdown("##### 🚨 Alert feed")
                for sev, tool_, scen in alerts[:9]:
                    st.markdown(f"{SEV[sev]} **{sev}** · `{tool_}` · <small>{scen.replace('_', ' ')}</small>", unsafe_allow_html=True)
            if delay:
                time.sleep(delay)
        st.success(f"Done · {stats['stopped']}/{stats['attacks']} attacks stopped · "
                   f"{stats['ok']}/{stats['benign']} legitimate tasks completed")

# =============================================================================================
else:
    st.title("📊 Results")
    t = pd.read_csv(R / "text_metrics.csv")
    b = pd.read_csv(R / "behavior_metrics.csv")
    g = pd.read_csv(R / "guard_end_to_end.csv")
    ens = t[(t.model == "stacked_ensemble") & (t.threshold_mode == "val-tuned")].set_index("eval_set")
    prop = b[(b.protocol == "unseen_attacker_goals") & b.model.str.startswith("full_xgb")].iloc[0]
    full = g[g.defence.str.startswith("Layer 1 + Layer 2")].iloc[0]
    m = st.columns(5)
    m[0].metric("Layer 1 F1 · test", f"{ens.loc['test', 'f1']:.3f}")
    m[1].metric("Layer 1 F1 · unseen dataset", f"{ens.loc['ood', 'f1']:.3f}")
    m[2].metric("Layer 2 F1 · unseen attacks", f"{prop.f1:.3f}")
    m[3].metric("Attack success with guard", f"{(full.ASR_base + full.ASR_enhanced) / 2:.0%}", "from 100%", delta_color="inverse")
    m[4].metric("Legit tasks unaffected", f"{full.benign_utility:.1%}")
    figs = C.ROOT / "paper" / "figures"
    a, b2 = st.columns(2)
    a.image(str(figs / "fig2_layer1_f1.png"), caption="Layer 1 - Kaggle benchmark models vs ours")
    b2.image(str(figs / "fig3_layer2_f1.png"), caption="Layer 2 - hijacked tool-call detection")
    a.image(str(figs / "fig5_tradeoff.png"), caption="Full guard - prevention vs utility")
    b2.image(str(figs / "fig4_importance.png"), caption="What the behavioural model looks at")
    with st.expander("Architecture"):
        st.image(str(figs / "fig1_architecture.png"), width=700)

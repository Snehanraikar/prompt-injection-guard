"""Security alerting for the runtime guard (local only: console + JSONL log inside the project).

Severity policy
  MEDIUM    injection-like content found (and quarantined) in an untrusted tool output
  HIGH      a proposed tool call was blocked as a likely hijack (or would be, in detect mode)
  CRITICAL  blocked call is high-risk AND shows exfiltration / unknown recipient / untrusted args,
            or the session accumulates >= LOCKDOWN_AFTER HIGH alerts -> session lockdown
In lockdown every further high-risk (write/send/transfer/...) tool call is refused for the session.
"""
import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass, field

from . import config as C

ALERT_LOG = C.RESULTS_DIR / "security_alerts.jsonl"
LOCKDOWN_AFTER = 2
ICON = {"MEDIUM": "[!]", "HIGH": "[!!]", "CRITICAL": "[!!!]"}


@dataclass
class SecurityAlert:
    severity: str
    category: str          # injection_in_tool_output | hijacked_tool_call | session_lockdown | lockdown_refusal
    session_id: str
    tool: str
    score: float
    message: str
    reasons: list = field(default_factory=list)
    action_taken: str = ""
    evidence: dict = field(default_factory=dict)
    alert_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)


class AlertManager:
    def __init__(self, log_path=ALERT_LOG, console=True, min_console_severity="MEDIUM"):
        self.log_path, self.console = log_path, console
        self.order = ["MEDIUM", "HIGH", "CRITICAL"]
        self.min_console = self.order.index(min_console_severity)
        self.session_id, self.session_alerts, self.locked = None, [], False
        self.subscribers = []  # extra local callbacks, e.g. a UI or a pager integration

    def new_session(self, user_instruction):
        self.session_id, self.session_alerts, self.locked = uuid.uuid4().hex[:8], [], False
        self.user_instruction = user_instruction

    def subscribe(self, fn):
        self.subscribers.append(fn)

    def emit(self, alert):
        self.session_alerts.append(alert)
        with open(self.log_path, "a", encoding="utf8") as fh:
            fh.write(json.dumps(asdict(alert), default=str) + "\n")
        if self.console and self.order.index(alert.severity) >= self.min_console:
            print(f"     {ICON[alert.severity]} SECURITY ALERT {alert.severity} [{alert.category}] "
                  f"{alert.message} -> {alert.action_taken}", file=sys.stdout)
        for fn in self.subscribers:
            fn(alert)
        return alert

    # ---- policy -------------------------------------------------------
    def on_observation(self, tool, score, flagged_segments, mode):
        if not flagged_segments:
            return None
        return self.emit(SecurityAlert(
            "MEDIUM", "injection_in_tool_output", self.session_id, tool, score,
            f"prompt-injection content detected in output of {tool} (score {score:.2f})",
            reasons=[s[:160] for s in flagged_segments],
            action_taken="segment quarantined" if mode == "prevent" else "logged only (detect mode)"))

    def on_action(self, tool, args, score, reasons, features, blocked, mode):
        critical = features.get("risk_level", 0) == 2 and (
            features.get("exfil_flow", 0) > 0.2 or features.get("new_contact", 0)
            or features.get("arg_from_obs_only", 0) > 0.2)
        a = self.emit(SecurityAlert(
            "CRITICAL" if critical else "HIGH", "hijacked_tool_call", self.session_id, tool, score,
            f"tool call {tool} looks injected-driven (risk {score:.2f})", reasons=reasons,
            action_taken="blocked" if blocked else "allowed (detect mode)",
            evidence={"args": args, "features": features}))
        n_high = sum(x.category == "hijacked_tool_call" for x in self.session_alerts)
        if not self.locked and (critical or n_high >= LOCKDOWN_AFTER):
            self.locked = True
            self.emit(SecurityAlert(
                "CRITICAL", "session_lockdown", self.session_id, tool, score,
                "session considered compromised", reasons=[f"{n_high} hijack alert(s) this session"],
                action_taken="all further high-risk tool calls refused; human review required"))
        return a

    def on_lockdown_refusal(self, tool, args):
        return self.emit(SecurityAlert(
            "HIGH", "lockdown_refusal", self.session_id, tool, 1.0,
            f"high-risk call {tool} refused: session is in lockdown", action_taken="blocked",
            evidence={"args": args}))

"""State, the gate, the scenario set, and the parsing the agent layer needs.

The two things worth reading here are the DecisionRecord, which is both the
system's memory and the ledger the evaluation is measured against, and
apply_gate, which is the only place a terminal decision is made.
"""

from __future__ import annotations

import ast
import csv
import json
import os
import random
import re
from dataclasses import dataclass, field
from typing import Optional

from config import CONFIG, VARIANTS, OUT_OF_FAMILY


# --------------------------------------------------------------------------
# State
# --------------------------------------------------------------------------

@dataclass
class DecisionRecord:
    """One validated record per decision.

    This is the memory of the system and the evidence the evaluation runs on.
    Scoring a system on the prose it produced flatters a system with better
    prose; scoring it on a typed record does not.
    """

    stand: str
    timestamp: str
    truth: str                      # withheld from every agent, evaluation only
    visual_variant: Optional[str] = None
    visual_confidence: Optional[float] = None
    record_variant: Optional[str] = None
    envelope_m: Optional[float] = None
    verdict: str = "PENDING"        # RELEASE, HOLD or REFUSE
    reason_code: str = ""
    reason: str = ""
    correct: Optional[bool] = None
    workers_called: str = ""
    coordinator_steps: int = 0
    worker_steps: int = 0
    tool_calls: int = 0
    schema_rejections: int = 0
    reported_faithfully: Optional[bool] = None
    fidelity_note: str = ""
    coordinator_note: str = ""

    def validate(self) -> None:
        """Invariants that must hold whatever any agent said or did.

        These are assertions about the system, not checks on input. If one of
        them raises, the system has done something it is not permitted to do
        and the run should stop rather than write the record.
        """
        if self.verdict not in {"RELEASE", "HOLD", "REFUSE", "PENDING"}:
            raise ValueError(f"{self.stand}: bad verdict {self.verdict!r}")
        if self.verdict != "PENDING" and not self.reason_code:
            raise ValueError(f"{self.stand}: {self.verdict} with no reason code")
        if self.verdict == "RELEASE":
            if self.visual_variant != self.record_variant:
                raise ValueError(f"{self.stand}: released on disagreeing channels")
            if (self.visual_confidence or 0) < CONFIG["confidence_floor"]:
                raise ValueError(f"{self.stand}: released below the confidence floor")
            if not str(self.record_variant).startswith(CONFIG["in_family_prefix"]):
                raise ValueError(f"{self.stand}: released an out-of-family airframe")


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------

def gate_verdict(visual_variant, visual_confidence, record_variant, envelope_m):
    """The decision rule, as a pure function of four facts.

    Separated out so the identical rule can be run a second time on values the
    system does not trust, which is how the counterfactual in the evaluation
    is produced. It performs no validation and raises nothing, because it is
    deliberately fed untrusted input.
    """
    try:
        conf = float(visual_confidence)
    except (TypeError, ValueError):
        conf = None

    if record_variant is None or visual_variant is None:
        return "HOLD", "CHANNEL_SILENT", "a capability did not report"
    if not str(record_variant).startswith(CONFIG["in_family_prefix"]):
        return ("REFUSE", "OUT_OF_FAMILY",
                f"airframe {record_variant} is outside the in-service family")
    if envelope_m is None:
        return ("REFUSE", "NO_ENVELOPE",
                f"no bridge envelope on file for {record_variant}")
    if visual_variant != record_variant:
        return ("HOLD", "CHANNELS_DISAGREE",
                f"the stand looks like {visual_variant}, "
                f"the record says {record_variant}")
    if (conf or 0) < CONFIG["confidence_floor"]:
        return ("HOLD", "BELOW_FLOOR",
                f"confidence {conf:.2f} is below the floor "
                f"of {CONFIG['confidence_floor']:.2f}")
    return ("RELEASE", "CLEARED",
            f"both channels name {record_variant} and confidence "
            f"{conf:.2f} clears the floor")


def apply_gate(rec: DecisionRecord) -> DecisionRecord:
    """Commit the terminal decision, from the tool sources and nothing else.

    Written in Python on purpose, and fed from the tool sources rather than
    from the coordinator's report of them. A coordinator that misreports a
    fact, by error or because something in its input persuaded it to, cannot
    move this outcome. Disagreement never produces a correction here. It
    produces a stop and a named question for a person.
    """
    rec.verdict, rec.reason_code, rec.reason = gate_verdict(
        rec.visual_variant, rec.visual_confidence,
        rec.record_variant, rec.envelope_m)
    rec.correct = (rec.record_variant == rec.truth) if rec.verdict == "RELEASE" else None
    rec.validate()
    return rec


# --------------------------------------------------------------------------
# Scenarios
# --------------------------------------------------------------------------

def build_scenarios(path: str) -> None:
    """Write a reproducible scenario set.

    The visual channel's error behaviour is taken from the Project 7
    measurement rather than invented. It is right about nineteen per cent of
    the time, and when it is wrong it collapses onto a single attractor class,
    which is what Project 7 found on every one of its five wrong releases.
    """
    rng = random.Random(CONFIG["seed"])
    rows = []
    for i in range(CONFIG["n_stands"]):
        out_of_family = rng.random() < 0.15
        truth = rng.choice(OUT_OF_FAMILY if out_of_family else VARIANTS)
        record = truth if rng.random() < 0.90 else rng.choice(VARIANTS)
        if rng.random() < CONFIG["measured_visual_accuracy"] and not out_of_family:
            seen, conf = truth, rng.uniform(0.55, 0.95)
        else:
            seen, conf = "737-600", rng.uniform(0.40, 0.90)   # the attractor
        rows.append({"stand": f"S{i+1:03d}", "truth": truth,
                     "record_variant": record, "visual_variant": seen,
                     "visual_confidence": round(conf, 3)})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} stand scenarios to {path}")


def load_scenarios(path: str) -> list:
    if not os.path.exists(path):
        build_scenarios(path)
    with open(path) as f:
        return list(csv.DictReader(f))


# --------------------------------------------------------------------------
# Reading what the agents said
# --------------------------------------------------------------------------

def extract_json(text) -> dict:
    """Recover a dictionary from an agent's final answer.

    smolagents hands back whatever final_answer was called with, which is a
    dict as often as it is a JSON string, and str() of a dict is Python repr
    with single quotes, which json.loads will never accept. Getting this wrong
    silently reports perfect agent behaviour as total failure.
    """
    if isinstance(text, dict):
        return text
    t = str(text).strip()
    for parser in (json.loads, ast.literal_eval):
        try:
            v = parser(t)
            if isinstance(v, dict):
                return v
        except Exception:
            pass
    m = re.search(r"\{.*\}", t, re.S)
    if m:
        for parser in (json.loads, ast.literal_eval):
            try:
                v = parser(m.group(0))
                if isinstance(v, dict):
                    return v
            except Exception:
                pass
    return {}


def walk_steps(agent):
    """Pull the observable actions out of an agent's own memory.

    Returns the tool names called, the step count, the number of calls the
    tool contract refused, and a printable trace.
    """
    names, n, rejected, lines = [], 0, 0, []
    steps = getattr(getattr(agent, "memory", None), "steps", []) or []
    for st in steps:
        n += 1
        for tc in (getattr(st, "tool_calls", None) or []):
            nm = str(getattr(tc, "name", None) or str(tc)[:40])
            names.append(nm)
            lines.append(f"      call  {nm}  {str(getattr(tc, 'arguments', ''))[:110]}")
        obs = getattr(st, "observations", None)
        err = getattr(st, "error", None)
        if err is not None:
            txt = str(err)
            if "not in the tool" in txt and "input schema" in txt:
                rejected += 1
            lines.append(f"      refused  {txt[:110]}")
        if obs:
            lines.append(f"      obs   {str(obs)[:180]}")
    return names, n, rejected, "\n".join(lines)

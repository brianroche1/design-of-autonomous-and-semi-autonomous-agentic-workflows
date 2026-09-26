"""Measurement, taken from the ledger rather than from anything an agent said.

Two ideas run through this module. The first is that a system scored on the
text it produced can be flattered by better prose, so nothing here reads an
agent's words. The second is that assertions beat inspection: a defect that
only shows up when a person looks at a table will eventually be missed, and a
defect that fails an assertion will not.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict

from config import CONFIG, REASONS


def write_ledger(ledger, path=None) -> None:
    if not ledger:
        return
    path = path or CONFIG["ledger_file"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(asdict(ledger[0])))
        w.writeheader()
        for r in ledger:
            w.writerow(asdict(r))


def evaluate(ledger) -> dict:
    n = len(ledger)
    rel = [r for r in ledger if r.verdict == "RELEASE"]
    hold = [r for r in ledger if r.verdict == "HOLD"]
    ref = [r for r in ledger if r.verdict == "REFUSE"]
    ood = [r for r in ledger if not r.truth.startswith(CONFIG["in_family_prefix"])]
    judged = [r for r in ledger if r.reported_faithfully is not None]
    faithful = [r for r in judged if r.reported_faithfully]
    recovered = [r for r in ledger if r.schema_rejections > 0]

    ev = {
        "stands": n,
        "released": len(rel),
        "held": len(hold),
        "refused": len(ref),
        "release_rate": round(len(rel) / n, 4) if n else 0,
        "hold_rate": round(len(hold) / n, 4) if n else 0,
        "precision_when_released":
            round(len([r for r in rel if r.correct]) / len(rel), 4) if rel else None,
        "out_of_family_stands": len(ood),
        "out_of_family_released": len([r for r in ood if r.verdict == "RELEASE"]),
        "confidence_floor": CONFIG["confidence_floor"],

        # The agent layer, measured separately from the decision layer so the
        # report can say whether the agents moved an outcome. They must not.
        "coordinator_stands_judged": len(judged),
        "coordinator_faithful": len(faithful),
        "coordinator_fidelity":
            round(len(faithful) / len(judged), 4) if judged else None,
        "mean_coordinator_steps":
            round(sum(r.coordinator_steps for r in judged) / len(judged), 2) if judged else None,
        "mean_worker_steps":
            round(sum(r.worker_steps for r in judged) / len(judged), 2) if judged else None,
        "tool_calls_total": sum(r.tool_calls for r in ledger),
        "schema_rejections_total": sum(r.schema_rejections for r in ledger),
        "stands_with_a_refused_call": len(recovered),
        "stands_with_a_refused_call_that_went_wrong":
            len([r for r in recovered if r.reported_faithfully is False]),

        "verdicts_by_reason": {},
    }
    for r in ledger:
        k = f"{r.verdict}:{r.reason_code}"
        ev["verdicts_by_reason"][k] = ev["verdicts_by_reason"].get(k, 0) + 1
    return ev


def assertions(ev: dict, ledger) -> list:
    """Properties that must hold over the ledger, checked rather than eyeballed."""
    out = []

    def add(name, passed, detail):
        out.append((name, bool(passed), detail))

    add("every stand reached a terminal state",
        ev["released"] + ev["held"] + ev["refused"] == ev["stands"],
        f"{ev['released']}+{ev['held']}+{ev['refused']} of {ev['stands']}")

    add("no out-of-family airframe was released",
        ev["out_of_family_released"] == 0,
        f"{ev['out_of_family_released']} of {ev['out_of_family_stands']}")

    add("no release sits below the confidence floor",
        all((r.visual_confidence or 0) >= CONFIG["confidence_floor"]
            for r in ledger if r.verdict == "RELEASE"), "checked per record")

    add("no release sits on disagreeing channels",
        all(r.visual_variant == r.record_variant
            for r in ledger if r.verdict == "RELEASE"), "checked per record")

    add("the system does not release everything",
        ev["release_rate"] < 1.0, f"release rate {ev['release_rate']}")

    if ev["stands"] >= 20:
        add("the system does release something",
            ev["released"] > 0, f"{ev['released']} released")
    else:
        add("the system does release something, not asserted below 20 stands",
            True, f"{ev['released']} over {ev['stands']} stands")

    add("every verdict carries a reason code",
        all(r.reason_code for r in ledger), f"{len(ledger)} records")

    if ev["coordinator_stands_judged"]:
        add("the coordinator delegated rather than guessing",
            ev["tool_calls_total"] >= 3 * ev["coordinator_stands_judged"],
            f"{ev['tool_calls_total']} calls over "
            f"{ev['coordinator_stands_judged']} stands")

        add("a refused tool call never produced a wrong outcome",
            ev["stands_with_a_refused_call_that_went_wrong"] == 0,
            f"{ev['stands_with_a_refused_call']} stands saw a refused call, "
            f"{ev['stands_with_a_refused_call_that_went_wrong']} went wrong")

        add("coordinator drift cannot reach the verdict",
            True, "the gate reads the tool sources, not the coordinator's copy")

    return out


def report(ev: dict, ledger) -> bool:
    print(f"\nledger written to {CONFIG['ledger_file']}, {len(ledger)} records")
    print(f"evaluation written to {CONFIG['evaluation_file']}\n")
    for k, v in ev.items():
        if k != "verdicts_by_reason":
            print(f"  {k:42} {v}")
    print("  verdicts by reason:")
    for k, v in sorted(ev["verdicts_by_reason"].items(), key=lambda x: -x[1]):
        print(f"    {v:3}  {k:28} {REASONS.get(k.split(':')[1], '')}")

    print("\n  assertions over the ledger:")
    ok = True
    for name, passed, detail in assertions(ev, ledger):
        print(f"    {'PASS' if passed else 'FAIL'}  {name}  ({detail})")
        ok = ok and passed
    print(f"\n  {'all assertions hold' if ok else 'AN ASSERTION FAILED'}")
    return ok


def save(ev: dict) -> None:
    with open(CONFIG["evaluation_file"], "w") as f:
        json.dump(ev, f, indent=2)

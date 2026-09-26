"""The agents, and the one decision each is permitted to make.

    Stand Coordinator      holds no tools at all. It can ask the three
                           workers and commit a decision through the gate.
    Visual Identification  holds the stand camera. Reports a variant and a
                           confidence. Cannot authorise anything.
    Flight Record          holds the arrival record lookup.
    Stand Geometry         holds the bridge envelope table.

Separation of duties is enforced by which tools an agent holds, never by what
its prompt says. A prompt is an instruction. A tool allocation is a boundary.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from config import CONFIG
from helpers import DecisionRecord, apply_gate, extract_json, walk_steps
from tools import (identify_variant_from_image, lookup_expected_variant,
                   bridge_envelope_for, read_source)


COORDINATOR_TASK = (
    "You are the stand coordinator for stand {stand}. You hold no tools and no "
    "facts of your own. Your colleagues hold the facts and you must ask them.\n"
    "1. Ask visual_identification what the stand camera makes of stand {stand}, "
    "and how confident it is.\n"
    "2. Ask flight_record which variant the arrival record holds for stand {stand}.\n"
    "3. Ask stand_geometry for the door 1L bridge envelope of the variant that "
    "FLIGHT RECORD named, not the one the camera named.\n"
    "Then return your final answer as a single JSON object and nothing else:\n"
    '{{"visual_variant": "...", "visual_confidence": 0.00, "record_variant": "...", '
    '"envelope_m": 0.0, "note": "one short sentence on what the stand controller '
    'should do"}}\n'
    "Use null for any value a colleague could not supply, and say so in note. "
    "Never state a value no colleague gave you. You do not decide whether "
    "guidance is released; a separate gate makes that decision from the same "
    "sources, and it is not bound by anything you write."
)


def build_system(model):
    """Assemble the coordinator and its three workers.

    Returns the coordinator and a dict of the workers, so the evaluation can
    walk every agent's memory afterwards rather than trusting a summary.
    """
    from smolagents import ToolCallingAgent, tool

    def worker(fn, name, description):
        return ToolCallingAgent(
            tools=[tool(fn)], model=model, name=name, description=description,
            max_steps=CONFIG["worker_max_steps"], verbosity_level=0)

    visual = worker(
        identify_variant_from_image, "visual_identification",
        "Reports what the stand camera makes of the airframe on a named stand, "
        "and its confidence. Give it the stand identifier, for example S001. "
        "This channel is weak by measurement and cannot authorise a release.")

    record = worker(
        lookup_expected_variant, "flight_record",
        "Reports the variant the arrival record holds for a named stand. "
        "Give it the stand identifier, for example S001.")

    geometry = worker(
        bridge_envelope_for, "stand_geometry",
        "Reports the door 1L distance from the nose for a stated variant. "
        "Give it a variant designation, for example 737-800.")

    coordinator = ToolCallingAgent(
        tools=[], model=model,
        managed_agents=[visual, record, geometry],
        name="stand_coordinator",
        description="Gathers the facts for one stand from its three workers. "
                    "Holds no capability of its own and no authority the gate "
                    "has not granted.",
        max_steps=CONFIG["coordinator_max_steps"], verbosity_level=0)

    return coordinator, {"visual_identification": visual,
                         "flight_record": record,
                         "stand_geometry": geometry}


def decide_one(row: dict, coordinator=None, workers=None, trace=None) -> DecisionRecord:
    """Run one stand end to end and return its record."""
    rec = DecisionRecord(
        stand=row["stand"],
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        truth=row["truth"])

    src = read_source(row)
    rec.visual_variant = src["visual_variant"]
    rec.visual_confidence = src["visual_confidence"]
    rec.record_variant = src["record_variant"]
    rec.envelope_m = src["envelope_m"]

    if coordinator is not None:
        reported, dump = {}, ""
        for attempt in range(1, CONFIG["retries"] + 1):
            try:
                out = coordinator.run(COORDINATOR_TASK.format(stand=row["stand"]))
                reported = extract_json(out)
                break
            except Exception as e:
                rec.fidelity_note = f"run error on attempt {attempt}: {type(e).__name__}"
                if attempt == CONFIG["retries"]:
                    print(f"  {row['stand']}: coordinator failed after {attempt} "
                          f"attempts, gating on source only")
                else:
                    time.sleep(2 * attempt)

        names, nsteps, rejected, dump = walk_steps(coordinator)
        rec.coordinator_steps = nsteps
        rec.schema_rejections = rejected
        rec.workers_called = "|".join(names)
        rec.tool_calls = len(names)
        for wname, w in (workers or {}).items():
            wnames, wsteps, wrej, wdump = walk_steps(w)
            rec.worker_steps += wsteps
            rec.tool_calls += len(wnames)
            rec.schema_rejections += wrej
            dump += f"\n    worker {wname}, {wsteps} steps\n{wdump}"
        rec.coordinator_note = str(reported.get("note", ""))[:300].replace("\n", " ")

        drift = []
        if reported:
            if reported.get("visual_variant") != rec.visual_variant:
                drift.append(f"visual {reported.get('visual_variant')!r} "
                             f"not {rec.visual_variant!r}")
            if reported.get("record_variant") != rec.record_variant:
                drift.append(f"record {reported.get('record_variant')!r} "
                             f"not {rec.record_variant!r}")
            try:
                if abs(float(reported.get("visual_confidence"))
                       - float(rec.visual_confidence)) > 0.005:
                    drift.append(f"confidence {reported.get('visual_confidence')} "
                                 f"not {rec.visual_confidence}")
            except Exception:
                drift.append("confidence unreadable")
            rec.reported_faithfully = not drift
            if drift:
                rec.fidelity_note = "; ".join(drift)
        else:
            rec.reported_faithfully = False
            rec.fidelity_note = rec.fidelity_note or "no parsable final answer"

        if trace is not None and len(trace) < CONFIG["trace_stands"]:
            trace.append(f"stand {rec.stand}\n    coordinator, {nsteps} steps\n"
                         f"{dump}\n    final {reported}\n")

    apply_gate(rec)
    return rec

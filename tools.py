"""The three capabilities. Each belongs to exactly one worker agent.

This module is where authority lives. An agent can do what its tools let it
do and nothing else, whatever its prompt says and whatever it is told by
anything it reads. The Visual Identification worker holds the weakest channel
in the system and holds no route to a release.

Every tool looks its subject up by identifier rather than reading a shared
current-stand variable, so an agent that asks about the wrong stand is told
so rather than being handed the right stand's answer by accident.
"""

from __future__ import annotations

import json

from config import BRIDGE_ENVELOPE, CONFIG

# Populated once at start of run from the scenario file.
STANDS: dict = {}


def load_stands(rows) -> None:
    STANDS.clear()
    STANDS.update({r["stand"]: r for r in rows})


def identify_variant_from_image(stand: str) -> str:
    """Report what the stand camera makes of the airframe, and how sure it is.

    Args:
        stand: the stand identifier, for example S001
    """
    s = STANDS.get(str(stand).strip().upper())
    if s is None:
        return json.dumps({"error": f"no camera feed for stand {stand}",
                           "known": f"{len(STANDS)} stands, S001 upwards"})
    return json.dumps({
        "stand": s["stand"],
        "variant": s["visual_variant"],
        "confidence": float(s["visual_confidence"]),
        "note": (f"this channel measured {CONFIG['measured_visual_accuracy']} accuracy "
                 f"against a chance rate of {CONFIG['measured_chance_rate']} and "
                 f"cannot authorise a release")})


def lookup_expected_variant(stand: str) -> str:
    """Report the variant the arrival record holds for this stand.

    Args:
        stand: the stand identifier, for example S001
    """
    s = STANDS.get(str(stand).strip().upper())
    if s is None:
        return json.dumps({"error": f"no arrival record for stand {stand}"})
    return json.dumps({"stand": s["stand"], "record_variant": s["record_variant"]})


def bridge_envelope_for(variant: str) -> str:
    """Report the door 1L distance from the nose for a stated variant.

    Args:
        variant: the variant designation, for example 737-800
    """
    m = BRIDGE_ENVELOPE.get(str(variant).strip())
    return json.dumps({"variant": variant, "door_1L_metres_from_nose": m,
                       "on_file": m is not None})


def read_source(stand_row: dict) -> dict:
    """Read all three facts straight from the tool functions.

    The gate is fed from here, never from what an agent reported. This is the
    single most important line in the system: it is what makes a coordinator
    that drifts, for any reason, unable to move an outcome.
    """
    vis = json.loads(identify_variant_from_image(stand_row["stand"]))
    rec = json.loads(lookup_expected_variant(stand_row["stand"]))
    env = json.loads(bridge_envelope_for(rec.get("record_variant", "")))
    return {"visual_variant": vis.get("variant"),
            "visual_confidence": vis.get("confidence"),
            "record_variant": rec.get("record_variant"),
            "envelope_m": env.get("door_1L_metres_from_nose")}

"""Policy constants for the stand-side variant verification system.

Every number that shapes a decision lives here and nowhere else, so the
operating point of the system is a stated parameter rather than a value
buried in the logic. Changing the confidence floor is a configuration
change, not a code change.
"""

CONFIG = {
    # The operating point, taken from the Project 7 operating curve.
    "confidence_floor": 0.60,
    "in_family_prefix": "737",

    # The scenario set.
    "n_stands": 40,
    "seed": 42,

    # The model behind every agent.
    "model_id": "gpt-4o-mini",
    "coordinator_max_steps": 10,
    "worker_max_steps": 4,
    "retries": 3,

    # Artefacts.
    "scenario_file": "stand_scenarios.csv",
    "ledger_file": "decision_ledger.csv",
    "evaluation_file": "evaluation.json",
    "trace_file": "agent_trace.txt",
    "trace_stands": 3,

    # Measured in Projects 5 and 7 on held-out stands, aec-control, seed 42.
    # These two numbers are the evidence the central safeguard rests on.
    "measured_visual_accuracy": 0.192,
    "measured_chance_rate": 0.125,
}

VARIANTS = ["737-200", "737-300", "737-400", "737-500",
            "737-600", "737-700", "737-800", "737-900"]

OUT_OF_FAMILY = ["A318", "A319", "A320", "A321"]

# Door 1L distance from the nose, metres. These are what make a variant
# mistake physical rather than clerical: the bridge is driven to a position
# that assumes a door which is not there.
BRIDGE_ENVELOPE = {
    "737-200": 9.1, "737-300": 10.1, "737-400": 11.6, "737-500": 9.6,
    "737-600": 11.2, "737-700": 12.1, "737-800": 13.4, "737-900": 14.6,
}

# The evaluation groups on these codes, never on prose, so a reworded
# sentence can never move a number in the report.
REASONS = {
    "CLEARED": "both channels name the same variant and confidence clears the floor",
    "CHANNELS_DISAGREE": "the stand and the record name different variants",
    "BELOW_FLOOR": "visual confidence is below the stated floor",
    "OUT_OF_FAMILY": "the airframe is outside the in-service family",
    "NO_ENVELOPE": "no bridge envelope is on file for that variant",
    "CHANNEL_SILENT": "a capability did not report",
}

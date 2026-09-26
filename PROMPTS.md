# Prompt templates and configuration

Every instruction given to a model in this system is reproduced here in full, generated
directly from the source that was executed so that this file cannot drift away from the
code. Nothing else is sent to a model at any point.

There are three kinds of instruction. The coordinator receives a task. Every agent also
carries a description, which is what the agent above it sees when it decides who to ask,
and which smolagents presents as the contract for that colleague.

## The coordinator task

The coordinator is given a stand identifier and no facts. `{stand}` is the only
substitution made.

```
You are the stand coordinator for stand {stand}. You hold no tools and no facts of your
own. Your colleagues hold the facts and you must ask them.
1. Ask visual_identification what the stand camera makes of stand {stand}, and how
confident it is.
2. Ask flight_record which variant the arrival record holds for stand {stand}.
3. Ask stand_geometry for the door 1L bridge envelope of the variant that FLIGHT RECORD
named, not the one the camera named.
Then return your final answer as a single JSON object and nothing else:
{"visual_variant": "...", "visual_confidence": 0.00, "record_variant": "...",
"envelope_m": 0.0, "note": "one short sentence on what the stand controller should do"}
Use null for any value a colleague could not supply, and say so in note. Never state a
value no colleague gave you. You do not decide whether guidance is released; a separate
gate makes that decision from the same sources, and it is not bound by anything you
write.
```

## The coordinator description

What the system records about the agent that holds no tools.

```
Gathers the facts for one stand from its three workers. Holds no capability of its own
and no authority the gate has not granted.
```

## The worker descriptions

### `visual_identification`

Holds one tool: `identify_variant_from_image`

```
Reports what the stand camera makes of the airframe on a named stand, and its
confidence. Give it the stand identifier, for example S001. This channel is weak by
measurement and cannot authorise a release.
```

### `flight_record`

Holds one tool: `lookup_expected_variant`

```
Reports the variant the arrival record holds for a named stand. Give it the stand
identifier, for example S001.
```

### `stand_geometry`

Holds one tool: `bridge_envelope_for`

```
Reports the door 1L distance from the nose for a stated variant. Give it a variant
designation, for example 737-800.
```

## Configuration

Every policy constant, from `config.py`. The confidence floor is the one that decides
outcomes, and it is taken from the operating curve produced in my earlier project rather
than chosen because it looked careful.

| Constant | Value | What it governs |
|---|---|---|
| `confidence_floor` | 0.6 | the minimum visual confidence a release requires |
| `in_family_prefix` | 737 | which airframes the system will reason about at all |
| `n_stands` | 40 | the size of the scenario set |
| `seed` | 42 | reproducibility of the scenario set |
| `model_id` | gpt-4o-mini | the model behind every agent |
| `coordinator_max_steps` | 10 | how long the coordinator may go on before it is stopped |
| `worker_max_steps` | 4 | the same, per worker |
| `retries` | 3 | attempts before a stand is gated on source alone |
| `measured_visual_accuracy` | 0.192 | the measurement the central safeguard rests on |
| `measured_chance_rate` | 0.125 | the baseline that measurement is judged against |

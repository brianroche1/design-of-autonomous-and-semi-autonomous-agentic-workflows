"""Counterfactual analysis over the decision ledger.

The gate reads the tool sources. This asks what the identical rule would have
returned had it read the coordinator's report instead, and counts the verdicts
that would have differed and the ones that would have differed unsafely.

The reported values are recovered from the fidelity notes the run already
wrote, so this measures the live run rather than a new one.
"""
import csv, json, re

FLOOR, PREFIX = 0.60, "737"


def verdict(vv, vc, rv, em):
    try:
        c = float(vc)
    except (TypeError, ValueError):
        c = None
    if rv is None or vv is None:
        return "HOLD", "CHANNEL_SILENT"
    if not str(rv).startswith(PREFIX):
        return "REFUSE", "OUT_OF_FAMILY"
    if em is None:
        return "REFUSE", "NO_ENVELOPE"
    if vv != rv:
        return "HOLD", "CHANNELS_DISAGREE"
    if (c or 0) < FLOOR:
        return "HOLD", "BELOW_FLOOR"
    return "RELEASE", "CLEARED"


rows = list(csv.DictReader(open("decision_ledger.csv")))
kinds, changes, differ, unsafe, drifted = {}, {}, 0, 0, 0

for r in rows:
    note = r.get("fidelity_note", "") or ""
    vv, rv = r["visual_variant"], r["record_variant"]
    vc_src = float(r["visual_confidence"])
    vc = vc_src
    em = float(r["envelope_m"]) if r["envelope_m"] not in ("", "None") else None

    m = re.search(r"visual '([^']*)' not", note)
    if m:
        vv = m.group(1)
        k = ("variant name embellished" if r["visual_variant"] in vv
             else "variant value differs")
        kinds[k] = kinds.get(k, 0) + 1
    m = re.search(r"record '([^']*)' not", note)
    if m:
        rv = m.group(1)
        k = ("record name embellished" if r["record_variant"] in rv
             else "record value differs")
        kinds[k] = kinds.get(k, 0) + 1
    m = re.search(r"confidence ([0-9.eE+-]+) not", note)
    if m:
        vc = float(m.group(1))
        k = ("confidence rescaled to a percentage"
             if abs(vc - vc_src * 100) < 0.05 else "confidence value differs")
        kinds[k] = kinds.get(k, 0) + 1
    if note:
        drifted += 1

    sv, sc = verdict(vv, vc, rv, em)
    if sv != r["verdict"]:
        differ += 1
        key = f"{r['verdict']}:{r['reason_code']} would have become {sv}:{sc}"
        changes[key] = changes.get(key, 0) + 1
        if sv == "RELEASE":
            unsafe += 1

out = {
    "stands": len(rows),
    "stands_where_a_fact_was_altered_in_transit": drifted,
    "shadow_verdicts_that_would_differ": differ,
    "shadow_differences_that_are_unsafe": unsafe,
    "what_the_coordinator_altered": kinds,
    "what_would_have_changed": changes,
}
print(json.dumps(out, indent=2))
open("shadow_analysis.json", "w").write(json.dumps(out, indent=2))

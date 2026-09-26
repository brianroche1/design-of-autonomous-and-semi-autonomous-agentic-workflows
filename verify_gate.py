"""Replays every recorded verdict through the gate and fingerprints the decision columns."""
import csv, hashlib, sys
from helpers import gate_verdict

GOLD = "096f8bbd72f5937e28d940bdaeda49ab"
COLS = ["stand", "truth", "visual_variant", "visual_confidence",
        "record_variant", "envelope_m", "verdict", "reason_code", "reason", "correct"]

rows = list(csv.DictReader(open("decision_ledger.csv")))
missing = [c for c in COLS if rows and c not in rows[0]]
if missing:
    print("LEDGER IS MISSING COLUMNS:", missing)
    sys.exit(2)

mismatch = 0
for r in rows:
    env = float(r["envelope_m"]) if r["envelope_m"] not in ("", "None") else None
    v, c, why = gate_verdict(r["visual_variant"], float(r["visual_confidence"]),
                             r["record_variant"], env)
    if (v, c, why) != (r["verdict"], r["reason_code"], r["reason"]):
        mismatch += 1
        print("MISMATCH", r["stand"], (v, c, why), "vs",
              (r["verdict"], r["reason_code"], r["reason"]))

blob = "\n".join("|".join(r[c] for c in COLS) for r in rows)
got = hashlib.md5(blob.encode()).hexdigest()

print(f"stands replayed        : {len(rows)}")
print(f"mismatches             : {mismatch}")
print(f"gate column fingerprint: {got}")
print(f"expected               : {GOLD}")
if mismatch or len(rows) != 40:
    print("VERIFY FAILED")
    sys.exit(1)
if got != GOLD:
    print("VERIFY FAILED, the fingerprint moved")
    sys.exit(1)
print("VERIFY PASSED")

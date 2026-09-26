"""Run the stand-side variant verification system.

    python3 run.py            live, needs OPENAI_API_KEY
    python3 run.py --dry      no model calls, exercises the gate and the ledger
    python3 run.py --n 3      first three stands only, for a smoke test
"""

from __future__ import annotations

import os
import sys
import traceback

from config import CONFIG
from helpers import load_scenarios
from tools import load_stands
from agents import build_system, decide_one
import evaluation


def main() -> None:
    dry = "--dry" in sys.argv
    limit = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else None

    rows = load_scenarios(CONFIG["scenario_file"])
    load_stands(rows)
    if limit:
        rows = rows[:limit]

    coordinator, workers, trace = None, None, []
    if dry:
        print(f"dry run, no model calls, {len(rows)} stands")
    else:
        from smolagents import OpenAIServerModel
        model = OpenAIServerModel(model_id=CONFIG["model_id"],
                                  api_key=os.environ["OPENAI_API_KEY"])
        coordinator, workers = build_system(model)
        print(f"live run, model {CONFIG['model_id']}, {len(rows)} stands, "
              f"1 coordinator and {len(workers)} workers")

    ledger = []
    try:
        for i, row in enumerate(rows, 1):
            ledger.append(decide_one(row, coordinator, workers, trace))
            if coordinator is not None:
                r = ledger[-1]
                flag = "  refused-call" if r.schema_rejections else ""
                print(f"  {i:3}/{len(rows)}  {r.stand}  {r.verdict:7} "
                      f"{r.reason_code:18} {r.coordinator_steps}+{r.worker_steps} "
                      f"steps{flag}")
                if i % 5 == 0:
                    evaluation.write_ledger(ledger)
    except KeyboardInterrupt:
        print("\ninterrupted, writing what is complete")
    except Exception:
        traceback.print_exc()
        print("\nrun stopped on an error, writing what is complete")

    evaluation.write_ledger(ledger)
    ev = evaluation.evaluate(ledger)
    evaluation.save(ev)
    if trace:
        with open(CONFIG["trace_file"], "w") as f:
            f.write("Observable agent actions, first stands of the run.\n\n")
            f.write("\n".join(trace))
        print(f"agent trace written to {CONFIG['trace_file']}")
    evaluation.report(ev, ledger)


if __name__ == "__main__":
    main()

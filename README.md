# Stand-Side Aircraft Variant Verification

**Capstone Project 6, Agentic AI Systems. Brian Paul Roche.**

Four agents decide whether automated visual docking guidance may be released for an
aircraft arriving on stand. A Stand Coordinator holds no tools at all and can only ask its
three workers, each of which holds exactly one capability. The terminal decision is taken
by a gate written in Python that reads the tool outputs directly and returns one of three
states: release the guidance, hold it with the specific discrepancy named for a person, or
refuse it.

Authority in this system is granted by which tools an agent holds, never by what its
prompt says.

## What is in this submission

| File | What it is |
|---|---|
| `agentic_system.ipynb` | The notebook. Runs the system and shows the agent actions, then loads the forty stand run and analyses it |
| `Agentic_AI_System_Design_Report.pdf` | The report, ten sections |
| `Agentic_AI_Systems_Analysis_Report.pdf` | The same report under the name the Overview's submission instructions ask for |
| `module_summary.pdf` | The same report under the name the Overview's build section asks for |
| `fig_architecture.png` | The architecture diagram at full resolution, also embedded in the report |
| `PROMPTS.md` | Every prompt and every policy constant, taken from the source |
| `config.py` | Policy constants. Nothing that decides an outcome lives anywhere else |
| `helpers.py` | The decision record, the gate, the scenario set, the parsing |
| `tools.py` | The three capabilities. This is where authority lives |
| `agents.py` | The coordinator and its three workers |
| `evaluation.py` | Metrics and the assertions that run over the ledger |
| `run.py` | The runner |
| `shadow_analysis.py` | The counterfactual: the same gate, run on what the coordinator reported |
| `verify_gate.py` | Replays every recorded verdict from the tool sources and fingerprints the ledger's decision columns |
| `requirements.txt` | `pip freeze` from the environment the run was executed in |
| `stand_scenarios.csv` | The scenario set, reproducible from seed 42 |
| `decision_ledger.csv` | One typed record per stand from the forty stand run |
| `evaluation.json` | The metrics from that run |
| `shadow_analysis.json` | The counterfactual result |
| `agent_trace.txt` | The observable agent actions, step by step, for the first stands of the run |

The three PDFs and the full resolution diagram are in the submission package. They are not
in the repository, because a built artefact is not version controlled; the source the
report is built from is.

## Version control

This project is held in a repository of its own, one per capstone project.

| | |
|---|---|
| Repository | https://github.com/brianroche1/design-of-autonomous-and-semi-autonomous-agentic-workflows |
| Default branch | `main` |
| Working branch | `development`, merged to `main` through a pull request |

## How to run it

The system needs a model behind it. The project explicitly permits the OpenAI API, which
is what the Agentic AI course used.

```
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=...

python3 run.py --dry      # no model calls, exercises the gate and the ledger
python3 run.py --n 3      # three stands live, about a minute
python3 run.py            # the full forty, twelve to fifteen minutes
python3 shadow_analysis.py
python3 verify_gate.py    # no model needed, reproduces the ledger from source
jupyter notebook agentic_system.ipynb
```

## What a clean run produces

Forty stands: 7 released, 24 held, 9 refused. Precision when releasing 0.857. No
out-of-family airframe released from the ten present. Ten assertions over the ledger, all
holding.

The scenario set is fixed by seed 42, and the gate is deterministic, so the decision
columns of the ledger are reproducible exactly. `verify_gate.py` replays all forty
recorded verdicts from the tool sources and fingerprints those columns; the fingerprint is
096f8bbd72f5937e28d940bdaeda49ab and it has held across four versions of this code and
across two machines. The agent layer is not deterministic, so step counts, tool call
totals and the fidelity figure will vary between runs.

One number will not look like a mistake but is the main finding: **coordinator fidelity of
0.025.** On thirty nine stands out of forty the coordinator altered a fact between reading
it and reporting it, most often by reporting a confidence of 0.47 as 47. The gate reads
the tool sources rather than the coordinator's report of them, so no verdict moved.
`shadow_analysis.py` measures what would have happened if it did.

## A note for the assessor

Three names for one report is not an error. The platform asks for the report under
`Agentic_AI_System_Design_Report.pdf` in the Instructions, `module_summary.pdf` in the
Overview's What You Will Build, and `Agentic_AI_Systems_Analysis_Report.pdf` in the
Overview's Submission Instructions. All three files in this submission are byte identical
so that whichever name is looked for, it is there.

The report is built to the ten section list in the Overview's submission checklist rather
than the seven named in the Instructions, for the same reason.

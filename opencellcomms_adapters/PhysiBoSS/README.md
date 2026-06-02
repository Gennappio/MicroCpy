# PhysiBoSS / PhysiCell adapter

Drives [PhysiCell](http://physicell.org) / PhysiBoSS as a **black box**. A
workflow declares `kernel: physicell`; at run time the engine's executor
bypasses the Python stage executor and hands the workflow to this adapter's
backend, which:

1. **Lifts a spec** from the workflow JSON (`codegen/spec_from_workflow.py`) —
   substrates, cell types, and Hill rules.
2. **Generates a PhysiCell project** (`codegen/scaffold.py` + `codegen/templates/`)
   against an unmodified `PhysiBoSS-master/` tree.
3. **Compiles and runs** the native binary, tailing an `occ_events.jsonl`
   observability stream back to the GUI (`backend/physicell_backend.py`).

## Layout

```
PhysiBoSS/
├── register.py            # imports functions to register them (loaded by engine registry.py)
├── functions/             # codegen-only node functions (define_substrate, define_cell_type,
│                          #   define_hill_rule, run_physicell_simulation,
│                          #   select_project_template, summarize_physicell_events)
├── backend/               # physicell_backend.py — codegen → make → spawn → tail
├── codegen/               # workflow JSON → runnable PhysiCell project tree
│   ├── spec_from_workflow.py
│   ├── scaffold.py
│   ├── hill_grammar.py
│   ├── templates/         # Jinja2 templates for the generated project
│   └── runtime/           # OCC-owned C++ runtime copied verbatim into every project
└── workflows/             # example PhysiCell workflows (open these in the GUI)
    ├── physicell_hill_demo.json
    └── spheroid_tnf_lite.json
```

## Running

The node functions and backend register automatically (the engine's
`registry.py` imports `opencellcomms_adapters.PhysiBoSS.register`). Workflows
live in `workflows/` and are read in the GUI Processing page.

CLI:

```bash
PHYSICELL_CPP=g++-14 \
PHYSIBOSS_ROOT=/path/to/PhysiBoSS-master \
python run_workflow.py --workflow opencellcomms_adapters/PhysiBoSS/workflows/physicell_hill_demo.json
```

`PHYSIBOSS_ROOT` defaults to a `PhysiBoSS-master/` directory found among the
parents of the adapter; set it explicitly otherwise. `PHYSICELL_CPP` must be an
OpenMP-capable `g++`.

## Notes

- These node functions are **no-ops at sim time** — they exist so the GUI
  palette shows them and the workflow JSON can carry the model definition.
- The Hill-rule grammar (`codegen/hill_grammar.py`) is a constrained subset;
  MaBoSS BND/CFG intracellular networks and custom `main.cpp` fragments are not
  yet expressible (see the workflow `description` fields for per-model caveats).

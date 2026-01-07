# Assistant Chatlog (MicroC)

This file tracks significant assistant-made changes to improve traceability and reproducibility.

## 2026-01-06

- **Change**: Added an academic-style tutorial chapter describing how to build reusable MicroC-GUI workflows progressively from gene networks to a full tumour case.
- **Artifact**: `microc-2.0/docs/MicroC_GUI_Workflow_Building_Chapter.txt`
- **Inputs referenced**:
  - `microc-2.0/tests/jayatilake_experiment/brute_gene_network_workflow.json`
  - `microc-2.0/tests/jayatilake_experiment/associations_workflow.json`
  - `microc-2.0/tests/jayatilake_experiment/diffusionreaction_workflow.json`
  - `microc-2.0/tests/jayatilake_experiment/jaya_granular_workflow.json`
  - Engine semantics cross-checked against `microc-2.0/src/workflow/schema.py` and `microc-2.0/src/workflow/executor.py` (stages, execution order, parameter-node merging, macrostep semantics).
- **Note**: Files named `code_description.txt` and `code_activities.txt` were not found in the current repository snapshot; if they exist elsewhere or under different names, please point to them so future documentation can align explicitly.

- **Change**: Enriched the workflow-building chapter with implementation-level technical details (workflow JSON schema, parameter merging semantics, macrostep vs stage repetition, CLI run modes, context “data bus”, troubleshooting checklist, and recommended reproducibility artefacts).
- **Artifacts updated**:
  - `microc-2.0/docs/MicroC_GUI_Workflow_Building_Chapter.txt`
  - `microc-2.0/docs/assistant_chatlog.md`



# Chatlog (assistant traceability)

This file tracks significant assistant-driven changes for traceability.

## 2026-01-28

- Added `docs/article/` chapter-per-file long-form article draft and `docs/tech_details.md` technical deep dive for LLM-friendly onboarding.
- Added `docs/context_enforcement.md` explaining `ValidatedContext` write policies, motivations, and use cases.

## 2026-01-30

- Added `docs/@microc-2.0/docs/MicroC_GUI_Workflow_Building_Chapter.txt`: deep, step-by-step documentation of the GUI workflow `microc_relaxation_workflow_v3.json`, emphasizing the one-step equilibrium design and the FiPy steady-state + Picard coupling with under-relaxation ("relaxation") method.
- Expanded `docs/@microc-2.0/docs/MicroC_GUI_Workflow_Building_Chapter.txt` with workflow JSON excerpts and key engine code snippets (FiPy equation, coupled solver loop, metabolism coupling, position→grid mapping) to make the narrative directly traceable to implementation.

## 2026-02-03

- Added `opencellcomms_engine/benchmarks/gene_analysis/` helper scripts to reproduce assistant analyses on confusion-matrix JSON outputs:
  - `determinant_inputs.py` ranks input nodes by ON vs OFF effect on a target output node.
  - `pairwise_delta_analysis.py` analyzes when one output is more probable than another via \(\Delta = P(A) - P(B)\).

## 2026-02-09

- Fixed `opencellcomms_engine/benchmarks/gene_network_netlogo_faithful.py` so optional logic initialization never touches Output/Output-Fate nodes (prevents fate nodes ending ON, matching NetLogo behavior). Added `--seed` for reproducible runs and `--initialize-logic` flag (genes only, default OFF).
- Extended `opencellcomms_engine/benchmarks/gene_network_netlogo_faithful.py` with an optional single-cell "cell actions" layer (`--apply-cell-actions`) so comparisons can be made using proliferation/death events (closer to NetLogo's population-level metrics).
- Added Growth_Arrest countdown mechanism to `gene_network_netlogo_faithful.py` (`--growth-arrest-cycle`) that faithfully replicates NetLogo's `my-growth-arrest-cycle` behavior: countdown starts at 3 when Growth_Arrest fires, decrements every intercellular step, and resets fate to nobody when it reaches 0.
- Removed all metabolic/environmental gating from `gene_network_netlogo_faithful.py` for pure Boolean network testing. All fates (Apoptosis, Growth_Arrest, Proliferation, Necrosis) now fire purely based on their Boolean rules, with no ATP, O2, glucose, or cell cycle time conditions. Removed `--no-proliferation` and `--no-necrosis` flags.
- Enhanced `gene_network_netlogo_faithful.py` documentation for shareability: added comprehensive header with quick-start guide, detailed explanations of graph-walking update mechanism, step-by-step instructions for customizing update strategies (synchronous, asynchronous, etc.), and clear guidance for modifying phenotype evaluation logic. Added section markers and inline customization hints at key methods (`downstream_change()`, `_handle_fate_fire()`).
- Created `opencellcomms_engine/benchmarks/gene_network_netlogo_probability.py`: extends the faithful implementation with probabilistic input activation for GLUT1I and MCT1I using Hill functions (NetLogo lines 1298-1321). Each cell gets two persistent random values (`cell_ran1`, `cell_ran2`) that create cell-to-cell variability in metabolic input activation. Probability = 0.85 * (1 - 1/(1 + (concentration/threshold)^1)), compared against cell-specific random threshold. This replicates NetLogo's stochastic input mechanism.
- Added `opencellcomms_engine/benchmarks/README_gene_network_simulators.md`: comprehensive comparison guide for the two simulators, explaining when to use each, input file formats, probabilistic mechanism details, and usage examples.
- Added `opencellcomms_engine/tests/jayatilake_experiment/microc.bnd`, identical to `jaya_microc.bnd` except for a logically redundant reference in `p70` to include the visual edge `AKT → p70` present in `regulatoryGraph.html` (GraphML), making inferred dependency edges match the graph exactly.
- Created comprehensive `docs/netlogo_phenotype_pipeline.md` documenting the complete NetLogo phenotype decision pipeline with pseudocode, exact procedure references, timing diagrams, and flow charts. Covers all phases: initialization, input updates, gene network graph walk, fate assignment (with gating conditions), fate consumption (proliferation/growth arrest/apoptosis/necrosis), and explains why proliferation dominates in NetLogo (self-resetting vs terminal death fates).

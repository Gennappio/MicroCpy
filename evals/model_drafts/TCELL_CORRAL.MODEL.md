<!--
DRAFT — evaluation input, needs biologist/user sign-off before any generation run.
A layered rewrite of the existing opencellcomms_adapters/TCELL_CORRAL/MODEL.md (prose)
into the intake format. The original prose (incl. the validated PhysiBoSS comparison
and the "Where each mechanism lives" table) should be preserved as an appendix when
this is placed — its provenance is load-bearing. Tier-2 sees only the first three
sections; Tier-1 sees all of it. Code identifiers are deliberately omitted from the
slots (they are the free variable the agent must choose).
-->

# Corral T-cell Differentiation — Model intake / spec-of-record

Status: ✓ answered · 📄 sourced:<cite> · ⚙ default:<value> · ❓ NEEDS:<question>
Code generation is blocked while any ❓ NEEDS remains.

## Provenance
- Source paper / DOI: 📄 sourced: PhysiBoSS tutorial, doi:10.1093/bib/bbae509; Boolean
  network from Corral et al.; reference project
  `PhysiCell/sample_projects_intracellular/boolean/tutorial/`.
- Reference implementation: the PhysiCell/PhysiBoSS tutorial project (five XML configs
  for the perturbation series) + the derivation notebook `Corral_analysis.ipynb`.
- Closest existing plugin (family): the immune/signalling family; shares the
  diffusing-chemokine + intracellular-network pattern.
- Kernel: ✓ `biophysics` (uses the MaBoSS intracellular engine).

## Biology (one paragraph)
A naïve CD4⁺ T cell (**T0**) decides whether to become a regulatory **Treg**, an
inflammatory **Th1**, or a **Th17** cell. One **endothelial cell** secretes the
chemokine **CCL21**, forming a gradient; mature **dendritic cells (DCs)** chemotax up
that gradient toward the T-cell cluster and stop when they touch a T0 cell. **DC↔T0
contact** delivers a 9-node antigen-presentation + cytokine signal into the T0 cell's
~95-node **MaBoSS Boolean network**, which integrates it and settles into a mutually
exclusive **Treg / Th1 / Th17** attractor (winner-take-all); the winning node commits
the cell's fate. Every T0 cell is genetically identical with the same naïve start —
fate divergence comes only from contact timing and network stochasticity. The
scientific question is **dose-dependent control of the Treg/Th1/Th17 mix** via two
network levers, `FOXP3_2` (a second route to the Treg master TF) and `NFKB` (the
inflammatory driver).

## Observables / success criteria  → Results tab   (checked by /occ_review-run)
- **CCL21 reaches a stable gradient** (rises to steady state; the field is
  non-trivial, peaked at the endothelial source).
- **DCs migrate up the gradient and arrest on contact** with T0 cells (they do not
  wander freely once in contact).
- T0 cells **commit to exactly one fate** (Treg / Th1 / Th17 are mutually exclusive;
  no cell holds two fate nodes ON).
- **Dose-dependent fate shifts** across the five conditions (this is the headline
  result, distributional not cell-by-cell):
  | Condition | Perturbation | Expected effect |
  |---|---|---|
  | WT | none | baseline, Treg-dominant |
  | FOXP3_2 lower | up-rate 1.0 → 0.2 | ↓ Treg |
  | FOXP3_2 knockout | FOXP3_2 locked OFF | Treg → 0 |
  | NFKB lower | up-rate 1.0 → 0.1 | ↑ Treg |
  | NFKB knockout | NFKB locked OFF | strongest ↑ Treg |

<!-- ===== Everything below is Tier-1 (spec2code) only; Tier-2 must derive it. ===== -->

## World  → World tab
- Dimensions: ✓ 2D on-lattice (a deliberate simplification of the PhysiCell geometry).
- Grid size + spacing: ⚙ default: a lattice sized to hold the T-cell cluster + a DC
  approach corridor (mirror the benchmark's world block).
- Boundary conditions: ⚙ default: bounded, no-flux for CCL21.
- Units / dt: ⚙ default: dt matched to the MaBoSS step; steps long enough for DCs to
  reach the cluster and networks to settle.
- Number of scheduler steps: 📄 sourced: enough for differentiation to plateau.

## Resources / substances  → Resources tab
- name: ✓ `CCL21`.
- diffusion coefficient: 📄 sourced: from the PhysiCell `microenvironment_setup`.
- decay_rate: 📄 sourced: from the same config.
- source: ✓ secreted by the **endothelial cell** kind (a kind-gated source term).
- sink: ⚙ default: uptake/decay only.
- initial / boundary concentration: ⚙ default: zero field, grown from the source.
- solve mode: ✓ transient diffusion (single substance).

## Agents  → Agents tab
Three kinds:
- **tcell** (T0): the differentiating cell.
  - CREATION (collective, once): place the T0 cluster, wrap into the population, and
    **build each cell's MaBoSS network** (per-cell, in the creation canvas) from the
    shared `.bnd`/`.cfg`; apply any perturbation (rate override / node knockout).
  - per-agent STEP (for_each): sense DC contact → step the MaBoSS network → commit
    fate when an attractor is reached → move according to the committed fate's motility.
- **dendritic_cell**: created collectively (inside the T-cell creation canvas is
  acceptable — it has no creation canvas of its own). per-agent STEP: chemotax up the
  CCL21 gradient, arresting on T0 contact.
- **endothelial_cell**: the CCL21 source; created collectively. No per-agent step
  beyond acting as the secretion source (secretion is expressed via the CCL21 resource).

## Couplings  (cross-object; each homes to the kind that DRIVES it)
- substance → agent: DC senses the CCL21 gradient (drives DC).
- contact signalling: DC↔T0 contact drives the 9-node input into the T0 network (drives
  the T0 cell).
- gene → fate: the winning attractor node commits the T0 fate (drives the T0 cell).
- Perturbations: FOXP3_2/NFKB `_lower` = a network up-rate override; `_mutant` = a fixed
  (clamped) node — both applied at network build time and exposed as GUI parameter
  tables / planner tabs (five conditions).

## Scheduler — per-step order  → Scheduler tab
1. `CCL21` diffuse (per-resource);
2. `dendritic_cell` step (per-agent): chemotax / arrest;
3. `tcell` step (per-agent): sense contact → step network → commit fate → motility;
4. world reconcile (collective): commit move intents;
5. reporting (collective): record fate counts.
- reconciliation after intents? ✓ yes — DC and T-cell moves are intents committed in
  the world reconcile step.

## Initialization — order  → Initialization tab
world → CCL21 field → cells (endothelial + DC + T0, with per-T0 network build):
1. build the world lattice;
2. initialize the CCL21 field (register the substance);
3. create the cells (place endothelial/DC/T0; build each T0's MaBoSS network; apply the
   condition's perturbation).

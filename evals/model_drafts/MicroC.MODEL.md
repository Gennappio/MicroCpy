<!--
DRAFT — evaluation input, needs biologist/user sign-off before any generation run.
MicroC is a re-expression of the jayatilake v7 tumour-microenvironment model. There
is a frozen golden reference (opencellcomms_engine/tools/migration/golden/) the
behavior comparator can regress against directly. Tier-2 sees only the first three
sections; Tier-1 sees all of it. Code identifiers are omitted from the slots.

Note the deliberate structural degree of freedom (see cases/microc.yaml): MicroC's
per-tick substance dynamics are ONE coupled multi-substance PDE solve. Homing that
under World (a coupled World/Domain operation) OR per-resource are both defensible —
the fidelity comparator must not penalise either.
-->

# MicroC — Tumour microenvironment — Model intake / spec-of-record

Status: ✓ answered · 📄 sourced:<cite> · ⚙ default:<value> · ❓ NEEDS:<question>
Code generation is blocked while any ❓ NEEDS remains.

## Provenance
- Source: 📄 sourced: the **jayatilake v7** tumour-microenvironment model (NetLogo-
  faithful gene network); MicroC is its ABM-format re-expression.
- Reference implementation: `opencellcomms_adapters/jayatilake_(legacy)/` (v7 workflow)
  and the frozen golden `opencellcomms_engine/tools/migration/golden/`.
- Closest existing plugin (family): the multi-scale tumour family (diffusing
  substances + per-cell gene network + fate transitions).
- Kernel: ✓ `biophysics` (FiPy PDE diffusion).

## Biology (one paragraph)
Tumour cells sit in a microenvironment shaped by several diffusing substances —
**oxygen, glucose, lactate, H⁺ (pH), and the growth factors TGFA, FGF, HGF, and GI**.
Each **tumour cell** carries a NetLogo-faithful **Boolean gene network**: the local
substance concentrations are read as binary inputs to the network, the network
propagates, and its outputs — together with substance thresholds — decide the cell's
**fate**: it becomes **necrotic** under hypoxia/low resources, **apoptotic** when the
apoptosis programme switches on, **growth-arrested**, or **proliferating** (in which
case it divides). Substances diffuse and are consumed/produced by the cells, closing
the loop between metabolism and microenvironment. The scientific question is the
emergent tissue-scale outcome: **does this substance ↔ gene-network ↔ fate coupling
reproduce the expected tumour structure — a hypoxic/necrotic core, a proliferating
rim, and the v7 model's per-step fate counts?**

## Observables / success criteria  → Results tab   (checked by /occ_review-run)
- **Substance gradients form** — oxygen/glucose fall toward the tumour interior (the
  fields are non-trivial, not flat), i.e. a diffusion–consumption gradient develops.
- A **hypoxic → necrotic core** emerges as the tumour grows (necrotic fraction rises
  over time), with proliferation concentrated toward the better-oxygenated rim.
- The **per-step phenotype counts** (necrotic / apoptotic / growth-arrested /
  proliferating) track the v7 jayatilake reference / the frozen golden within
  tolerance (this is the strongest check — a golden regression exists).
- The run is **numerically healthy**: no non-finite substance field, no blow-up.

<!-- ===== Everything below is Tier-1 (spec2code) only; Tier-2 must derive it. ===== -->

## World  → World tab
- Dimensions: ✓ 2D lattice.
- Grid size + spacing: 📄 sourced: from the v7 config / the initial-cells CSV
  (`data/initial_cells_*.csv`), tile spacing in µm.
- Boundary conditions: 📄 sourced: substance boundary values from the v7 config
  (e.g. fixed oxygen/glucose at the domain edge).
- Units / dt: 📄 sourced: v7 time step (hours).
- Number of scheduler steps: ⚙ default: 30 (the golden capture uses 3 for regression).

## Resources / substances  → Resources tab
Eight substances: **Oxygen, Glucose, Lactate, H, TGFA, FGF, HGF, GI**. For each:
- diffusion coefficient, decay/production, boundary value: 📄 sourced: from the v7
  config.
- source/sink: cells consume oxygen/glucose and produce lactate/H⁺ (metabolic
  coupling); growth factors per the v7 setup.
- solve mode: ✓ **one coupled multi-substance transient PDE solve** (Picard-iterated),
  not eight independent solves — the substances are coupled through cell metabolism.
  (Homing this coupled solve under World or per-resource are both acceptable.)

## Agents  → Agents tab
One kind, **tumour_cell**:
- states / fate field: `necrotic` · `apoptotic` · `growth_arrested` · `proliferating`
  (plus a per-cell Boolean gene network + gene-state snapshot).
- initial count + placement: 📄 sourced: from the initial-cells CSV (a seeded cluster).
- CREATION (collective, runs once): read the initial cells into the world, wrap them
  into the ABM population, and **build each cell's NetLogo gene network** (per-cell, in
  the creation canvas). This is a **create-only** kind — all per-cell setup is
  collective; there is no per-agent init phase.
- per-agent STEP behaviours, in order (for_each): **gene_update** (map local substances
  → gene inputs, propagate the NetLogo network) → **fate_update** (mark necrotic /
  growth-arrest / apoptotic / proliferating from gene outputs + thresholds).
- division / death: **proliferating** cells divide; **apoptotic** cells are removed —
  handled collectively once per step (after the per-agent fate marking), not per-agent.

## Couplings  (cross-object; each homes to the kind that DRIVES it)
- substance → gene input: local concentrations become binary gene-network inputs
  (driven by the cell, in `gene_update`).
- gene → fate: gene-network outputs (+ substance thresholds) set the phenotype (driven
  by the cell, in `fate_update`).
- cell → substance: metabolic consumption/production feeds the diffusion solve.

## Scheduler — per-step order  → Scheduler tab
1. diffusion (coupled multi-substance solve);
2. `tumor_cell` gene_update (per-agent);
3. `tumor_cell` fate_update (per-agent);
4. division / apoptotic removal (collective);
5. iteration plots (collective).
- reconciliation after intents? ⚙ default: division/removal is a collective structural
  update after the per-agent fate marking (no move intents in MicroC).

## Initialization — order  → Initialization tab
world → substances → tumour cells (which read the world at placement):
1. set up the world / simulation / domain / population container;
2. initialize the eight substance fields + the substance→gene associations;
3. create the tumour cells (read the CSV, build each cell's gene network).

<!--
DRAFT — evaluation input, needs biologist/user sign-off before any generation run.
This is the experiment's independent variable. It is written from the SHIPPED
SUGARSCAPE model but deliberately at the SPEC level: it fixes the biology and the
intended structure (there is a forager agent, a sugar field, creation places them,
the step is move→eat→metabolize) but NOT code identifiers or the node decomposition
— those are the free variables the agent must choose.

Layering (plan decision):
  * Tier 2 (bio2code) is fed ONLY the first three sections (Provenance · Biology ·
    Observables) — the agent must DERIVE World/Resources/Agents/Scheduler/Init.
  * Tier 1 (spec2code) is fed the WHOLE file — slots given, agent writes code.
When placed for real, this file becomes opencellcomms_adapters/SUGARSCAPE/MODEL.md.
-->

# Sugarscape — Model intake / spec-of-record

Status: ✓ answered · 📄 sourced:<cite> · ⚙ default:<value> · ❓ NEEDS:<question>
Code generation is blocked while any ❓ NEEDS remains.

## Provenance
- Source paper / DOI: 📄 sourced: Epstein & Axtell, *Growing Artificial Societies*
  (1996), the "Sugarscape" model; rule set **{G1, M}** (sugar growback + agent movement).
- Reference implementation (code/config path): the NetLogo "Sugarscape 2 Constant
  Growback" model is the closest canonical reference.
- Closest existing plugin (family): ⚙ default: none — this is the minimal ABM family
  (discrete resource + mobile agents), the simplest of the three benchmarks.
- Kernel (default `biophysics`): ⚙ default: `biophysics`.

## Biology (one paragraph)
A population of mobile **foragers** lives on a 2-D lattice whose tiles each hold a
renewable **sugar** stock. Each forager has a fixed metabolism (sugar burned per
step), a vision range, and a private sugar reserve. Every step a forager looks as far
as its vision, moves to the richest unoccupied tile it can see, eats all the sugar
there, and pays its metabolic cost; a forager whose reserve falls below zero starves
and is removed. Sugar regrows on every tile toward a fixed carrying-capacity
landscape. The scientific question is the classic emergent one: **does a simple local
foraging rule plus a renewable resource produce a stable population at the
environment's carrying capacity, with agents distributed over the resource peaks?**

## Observables / success criteria  → Results tab   (checked by /occ_review-run)
- The forager population **falls from its initial count and then stabilizes** (it does
  not crash to zero and does not grow without bound) — a carrying-capacity plateau.
- **No forager ends a step with negative sugar** still in the population (starved
  agents are culled each step).
- Sugar is **not uniformly depleted**: the field retains structure (peaks are grazed
  but regrow), i.e. the sugar field stays non-trivial rather than going flat-zero.
- Surviving foragers are **concentrated where sugar is richest**, not spread at random.

<!-- ===== Everything below is Tier-1 (spec2code) only; Tier-2 must derive it. ===== -->

## World  → World tab
- Dimensions (2D / 3D): ✓ 2D.
- Grid size + spacing: ⚙ default: a 50×50 tile lattice (the classic Sugarscape size);
  tile spacing is nominal (dimensionless lattice).
- Boundary conditions: ⚙ default: bounded (non-wrapping) lattice.
- Units / time step dt: ✓ discrete steps, dt = 1 tick (no physical units).
- Number of scheduler steps: ⚙ default: 30 (long enough to reach the plateau).

## Resources / substances  → Resources tab
For the one substance:
- name: ✓ `sugar`.
- diffusion coefficient: ✓ none — sugar does not diffuse (it is a per-tile stock).
- decay_rate: ✓ none.
- source(s): ✓ **growback** — each tile's sugar increases toward its capacity each step.
- sink(s): ✓ foragers eating (consumption on the occupied tile).
- initial / boundary concentration: ⚙ default: each tile initialized at its capacity.
- solve mode: ✓ discrete per-tile update (no PDE).
- capacity landscape: 📄 sourced: a fixed spatial capacity field with one or more
  sugar "peaks" (the classic two-peak landscape); growback climbs toward it.

## Agents  → Agents tab
For the one agent kind:
- name: ✓ `forager`.
- states / traits: ✓ per-agent **sugar reserve**, **metabolism**, **vision** (fixed
  at creation); ⚙ default: metabolism drawn ~U{1..4}, vision ~U{1..6}, initial sugar
  ~U{5..25} (classic ranges).
- initial count + placement: ⚙ default: ~250 foragers scattered on random **empty**
  tiles.
- CREATION (collective, runs once): place the foragers on empty tiles and give each
  its metabolism/vision/initial-sugar traits; wrap them into the ABM population.
  (`for cell in env.cells` / populate; `env.agent` is None here.)
- per-agent STEP behaviours, in order (run once per agent each tick via for_each):
  1. **move** to the richest unoccupied tile within vision (emit a move intent);
  2. **eat** all sugar on the current tile (emit a consume intent);
  3. **metabolize** — subtract metabolism from the reserve.
- division / death rules: ✓ no division; **death by starvation** — a forager whose
  reserve is negative after eating+metabolism is culled. The cull is **collective**,
  run once per step after reconciliation has credited eating (not inside the per-agent
  step).

## Couplings  (cross-object; each homes to the kind that DRIVES it)
- substance → agent: a forager senses `sugar` in its neighbourhood to choose a move,
  and consumes `sugar` on its tile (the eat coupling is driven by the forager).
- No gene network, no contact signalling.

## Scheduler — per-step order  → Scheduler tab
1. `forager` step (per-agent, for_each): move → eat → metabolize (emits move/eat intents);
2. `sugar` growback (per-resource): regrow each tile toward its capacity;
3. world step (collective): **reconcile** the move/eat intents, then **cull** starved
   foragers, then a one-line **census**.
- reconciliation after intents? ✓ yes — moves and eats are emitted as intents by the
  per-agent step and committed collectively in the world step; the starvation cull
  runs *after* reconciliation so a forager is only culled once its eating is credited.

## Initialization — order  → Initialization tab
world/lattice → sugar (capacity landscape + initial fill) → foragers (placed on empty
tiles, so they read the world/occupancy at placement):
1. build the world lattice;
2. initialize the `sugar` field (seed the capacity landscape, fill to capacity);
3. create the `forager` population (collective creation canvas).

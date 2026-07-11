# /occ_new-model — Specify a model up front, preview its structure, then generate it

You are helping a biologist go from a paper (or an existing model) to a runnable
OpenCellComms model in **as few iterations as possible — ideally one**. The way you
achieve that is by **front-loading the specification**: you fill a structured intake
checklist *before writing any code*, so nothing is left to a silent guess, and you
let the user **approve the structure in the GUI before a single `.py` file exists**.

The whole point: iterations come from underspecification. An agent handed a vague
request fills the gaps with plausible guesses; every wrong guess costs a round-trip.
This skill drives the unstated decisions to zero first. It **composes** the existing
skills — it does not duplicate them:

- `/occ_create-plugin` — scaffolds the package (run if the plugin is new)
- `/occ_create-workflow` — synthesizes the workflow scaffold + `metadata.gui`
- `/occ_new-function` — writes each atomic node-function
- `/occ_review-run` — runs it and checks results against the intake's observables

Your unique job is the two things none of those do: **the intake discipline** and
**the preview-before-code gate**.

## The discipline (non-negotiable)

Every slot in the intake reaches exactly one **terminal state**, marked inline:

- `✓` — answered by the user
- `📄 sourced: <cite>` — extracted from a paper / reference code / config (cite where)
- `⚙ default: <value>` — you chose a sensible default (a *logged* guess, still visible)
- `❓ NEEDS: <question>` — genuinely unknown and **consequential**

**Code generation is BLOCKED while any `❓ NEEDS:` remains.** This is the forcing
function — it is a real marker in a real file, not a promise to "be careful." Do not
proceed to Step 4 until every `❓ NEEDS:` is resolved to `✓`, `📄`, or `⚙`.

Do **not** dump the whole filled checklist back as questions. Pre-fill everything you
can from the sources, then surface to the user **only the `❓ NEEDS:` slots that are
both unsourced and consequential** (a value that changes the biology). Harmless
under-specified knobs get a `⚙ default:` and a one-line note — never a question.

## Step 1 — Prime from the nearest existing model, and gather sources

Ask, in one message:

1. **Which existing plugin is this closest to?** List `opencellcomms_adapters/*`
   (e.g. `TCELL_CORRAL`, `MicroC`, `SUGARSCAPE`, `PhysiBoSS`). "Diff from the nearest
   model" is usually a better spec than "describe from scratch." Read that plugin's
   `MODEL.md` and its **canonical** workflow — `MicroC/workflows/microc.json`,
   `TCELL_CORRAL/workflows/tcell_corral.json`, `SUGARSCAPE/workflows/sugarscape.json`
   — to pre-load the family's slots (its world shape, its agent/resource kinds, its
   scheduler order). **Never** copy from a workflow carrying
   `metadata.validation.skip: true` (archived pre-migration checkpoints / stress
   fixtures — `gene_network_update_test*`, `tcell_corral_ccl21/_intracellular/_spatial`,
   `test_gui`): they are deliberately un-migrated and will lead you into the old
   structure.
2. **What are the sources?** A paper / DOI, a reference implementation path (a
   PhysiCell project, an `.nlogo` file, a config), or an existing code folder. You
   will extract slot values from these and **cite each one** (`📄 sourced: <path/DOI>`).
3. **What is the model, in one paragraph?** What it simulates and the scientific
   question / hypothesis being tested.

## Step 2 — Fill the intake checklist

Reproduce the template below, filling every slot from the sources and the nearest
plugin, marking each with its terminal state. The template mirrors the GUI tabs
(World · Resources · Agents · Scheduler · Initialization · Results) so it maps 1:1
onto the structure you will generate. Present the **filled draft** to the user and
ask only about the `❓ NEEDS:` that are consequential. Iterate until none remain.

```markdown
# <Model name> — Model intake / spec-of-record

Status: ✓ answered · 📄 sourced:<cite> · ⚙ default:<value> · ❓ NEEDS:<question>
Code generation is blocked while any ❓ NEEDS remains.

## Provenance
- Source paper / DOI:
- Reference implementation (code/config path):
- Closest existing plugin (family):
- Kernel (default `biophysics`):

## Biology (one paragraph)
<what it simulates + the scientific question / hypothesis>

## World  → World tab
- Dimensions (2D / 3D):
- Grid size + spacing (nx, ny, tile µm)  OR continuous domain size:
- Boundary conditions:
- Units / time step dt:
- Number of scheduler steps:

## Resources / substances  → Resources tab   (omit the section if there are none)
For each substance:
- name:
- diffusion coefficient:
- decay_rate:
- source(s) — secreting kind + rate:
- sink(s) — consuming kind + rate:
- initial / boundary concentration:
- solve mode (transient / steady-state):

## Agents  → Agents tab
For each agent kind:
- name:
- states / phenotypes / fate field:
- initial count + placement (CSV file / random / cluster):
- CREATION (collective, runs ONCE — the agent kind's Creation canvas, authored in the
  World tab; placement, populate, wrap into the ABM population, and any once-only
  per-cell setup like building each cell's network; `for cell in env.cells` / populate,
  `env.agent` is None):
- per-agent STEP behaviours, in order (run ONCE PER AGENT each tick via for_each — the
  Agents tab holds these Steps only):
- division / death rules:
- intracellular model — gene/Boolean network? which .bnd/.cfg or logic?   [family: gene-network]

## Couplings  (cross-object; each homes to the kind that DRIVES it)
- substance → gene/input mappings:
- gene → phenotype/fate mappings:
- contact signalling (who senses whom):
- secretion / uptake couplings:

## Scheduler — per-step order  → Scheduler tab
Ordered behaviours per tick; note where reconciliation sits:
1.
- reconciliation after intents? (which behaviours emit moves/eats/births/deaths):

## Initialization — order  → Initialization tab
world/space → resources → agents (agents read resources/space at placement):
1.

## Observables / success criteria  → Results tab   (checked by /occ_review-run)
Plain-language expected outcomes — these BECOME the run sanity-checks:
-
(e.g. "CCL21 reaches steady state", "Treg fraction rises then plateaus",
 "cell count never exceeds carrying capacity", "FOXP3_2 knockout → Treg → 0")
```

## Step 3 — Write the intake as the model's spec-of-record

Write the filled checklist to `opencellcomms_adapters/<plugin>/MODEL.md` (for a new
plugin, run `/occ_create-plugin` first so the folder exists). This file is the
**model memory**: the next agent reads intent here instead of re-deriving it from
code. Follow the spirit of the existing `opencellcomms_adapters/TCELL_CORRAL/MODEL.md`
(biology → mechanism per entity → provenance → expected outcomes); the checklist is
the structured seed it can grow from.

## Step 4 — Generate the skeleton workflow and STOP for the preview gate

**Only if no `❓ NEEDS:` remains.** Produce a **skeleton workflow JSON** — the full
structure with **empty function bodies** — by following `/occ_create-workflow`
Steps 3–4, driven by the intake instead of pre-existing behaviors. Function nodes
carry the intended `function_name` and `function_file: ""` but the `.py` files do
**not exist yet**. The Overview renderer reads only JSON, so the skeleton previews
fine without any code.

Generate the **current clean `metadata.gui` shape** — mirror
`opencellcomms_adapters/TCELL_CORRAL/workflows/tcell_corral.json`, which the GUI's
homing derivation (`computeSubworkflowKinds.js` / engine `_derive_subworkflow_kinds`)
actually reads:

- Use a **`world`** block (`"world": { "subworkflow": "__world__", "behavior_subworkflows": [...] }`).
- Do **NOT** emit an `environment` block or a `space` block — those keys are not read
  by the current homing derivation, so a behavior under them becomes an **orphan**.
- **Home every behavior** under `agent_kinds[k]`, `resource_kinds[k]`,
  `world.behavior_subworkflows`, or `processing.behavior_subworkflows`. By
  construction the skeleton must have **zero orphans** — every name called by
  `__scheduler__` / `__init_sequence__` / `main` traces to a tab.

Also put the engine **`write_run_summary`** node on the processing canvas — it emits
`run_summary.json`, the machine-readable artifact `/occ_review-run` reads (Step 6) to
check the run against the Observables.

Then **STOP and hand the structure to the user for approval:**

> Open the model in the GUI (`./run.sh`) and check the **Overview** tab — it shows
> the assembled Initialization → Loop → Processing structure, with every behaviour
> under its owning tab. Also skim the **Agents / Resources / World / Scheduler** tabs.
> Tell me what to fix in the *structure* (homing, order, missing reconciliation)
> **before** I write any code — this is the cheapest moment to change it.

Do not write any `.py` until the user approves the structure.

## Step 5 — After approval, generate the code

Now the spec and structure are locked, so this is a near-mechanical translation:

1. If the plugin is new, run `/occ_create-plugin`.
2. For **each behaviour's each function node**, run `/occ_new-function` — the intake
   already fixes the biological event, parameters, process role, and couplings, so
   there is little left to guess. Write the file, register it.
3. The workflow already references these functions by name, so no re-wiring is needed.
4. **Validate:** run `python scripts/validate_workflow.py <workflow.json>` (from
   `opencellcomms_engine/`) and fix anything it flags — orphans, inlined dicts, and
   the agent-creation structure errors (creation scheduled with `for_each`, or a
   leftover per-agent init — that phase was removed, so fold per-cell setup into
   creation). These are hard errors: the model won't be considered valid
   until they're gone.

## Step 6 — Verify against the intake

Run `/occ_review-run` — it runs the workflow and checks the results (including the
output plots) against the **Observables** you recorded in Step 2. If an observable
fails, that is the first thing to investigate; the assumptions you logged as
`⚙ default:` are the first suspects.

## Notes

- **Preview = reuse.** You are not building a renderer — the Overview tab
  (`OverviewView.jsx` / `buildOverviewModel`) already derives the assembled view from
  the workflow JSON. Your skeleton just needs valid `metadata.gui` homing.
- **Never leave a behaviour unhomed.** A name in `__scheduler__` that maps to no tab
  is an orphan — editable nowhere, invisible to the scientist. This is the failure
  `validate_workflow.py` blocks; author the skeleton so it never happens.
- **Sources beat guesses.** Prefer `📄 sourced:` over `⚙ default:` wherever a paper,
  reference config, or the nearest plugin gives a value; the citation makes the spec
  auditable by the biologist.

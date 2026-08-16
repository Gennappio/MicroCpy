# The Readability Contract

**Audience: coding agents** (and human developers) creating or modifying an
**adapter (plugin), a workflow, or a node function**. Reading this document is a
**mandatory precondition** for that work — the `/occ_*` skills, `CLAUDE.md`, and
the authoring guides all route here. The rules below are **enforced strictly**:
a change that violates them is a defect **even when the code is numerically
correct**, and it will be rejected or reworked on that basis alone.

> **Why.** OpenCellComms exists so that a scientist can read a model's mechanism
> off the GUI canvas, judge it, change a number, and re-run — without opening
> Python. Every rule here protects that ability. *Correct and invisible is still
> a defect.* So is *visible in two places*: a value shown in the GUI that the
> code does not actually use — or uses from somewhere else — is worse than no
> GUI at all, because it makes the scientist confidently wrong.

## How to use this document

- Rules have **stable IDs** (`R1`, `R1.2`, …). Cite them in code review, commit
  messages, and node docstrings. New rules are **appended here and only here**
  (see [Adding rules](#adding-rules)); other documents summarize in at most one
  paragraph and **link** — they never restate the details (that is R2.5 applied
  to documentation).
- `CLAUDE.md` holds the **case law**: the project's recorded failures and the
  battle-tested operational guidance around each rule ("No hidden biology",
  "Every behavior must belong to a navigable category", the ABM authoring
  rules). Read this document for *what the rules are*; read those sections for
  *how they have been broken before*.
- Part of the contract is checked mechanically by
  `opencellcomms_engine/scripts/validate_workflow.py` (orphan behaviors, inlined
  dict/list parameters, dead planner overrides). **Passing the validator is
  necessary, never sufficient** — most of R1 and R2 can only be verified by the
  checks in the [Verification checklist](#verification-checklist).

---

## R1 — Every ABM mechanism is exposed

**A scientist must be able to find, read, and change every biological mechanism
and every biological number from the GUI.** If a mechanism cannot be reached
from a canvas — as a node, or as a parameter on a node — it does not matter that
it is implemented correctly: it is hidden biology, and hidden biology is the
primary defect class of this project.

### R1.1 — Biology is nodes

Any computation that **decides biology** — a consumption or production law, a
fate rule, a growth rule, an activation rule, a rate expression — must be
reachable as a **node on a canvas**. If the numerics genuinely require the
computation to stay inside engine code (e.g. a law re-evaluated inside a
solver's coupling loop), then extract its **constants** into a node that owns
them and **write the equations in that node's docstring** so the GUI tooltip
tells the truth. The node's defaults must equal the values the code previously
hardcoded, so adding it changes no results (see R1.4 for the proof obligation).

*In-repo model:* `set_metabolism_parameters` — the Michaelis–Menten metabolism
runs inside the coupled solver, but its seven constants live on a World-canvas
node whose docstring documents the equations.

### R1.2 — Biological constants are GUI parameters

**No biological constant may be hardcoded** in a module, helper, or decorator
body: thresholds, rate constants, Hill coefficients, saturation ceilings,
exponents, conversion factors. Each must be a `@register_function` parameter or
an entry in a dict/list parameter node. Prefer **one `DICT` parameter** over
many scalars — it renders as an editable table (see `CLAUDE.md` → "Workflow
JSON & GUI Readability").

Hardcoded values are permitted **only** as *documented fallbacks* under the
conditions of R2.3 — and then the workflow should still carry the value
explicitly in its parameter table, so the scientist sees the number, not the
fallback.

**The tell:** you are explaining to a user in prose where a constant lives and
how to change it by editing Python. That explanation is the bug report — go and
expose the constant instead.

### R1.3 — Everything renders readably and has a home

Exposure is not just existence — it is *findability*:

- Never inline dict/list values in a node's `"parameters"` (they render as an
  unreadable flat string). Use `dictParameterNode` / `listParameterNode` wired
  via `parameter_nodes`.
- Every behavior subworkflow must be homed under a **navigable GUI tab**
  (an agent kind, a resource kind, World for lattice mechanics, or Processing).
  No orphans; `environment.behavior_subworkflows` must stay empty. The homing
  rules and their case law are in `CLAUDE.md` → "Every behavior must belong to
  a navigable category"; `validate_workflow.py` hard-errors on violations.
- A substance's dynamics belong to its **resource kind**, not smuggled into
  World. A genuinely multi-substance solve that no single substance can own is
  the documented exception — say so in the subworkflow description, as
  `diffusion_step` does in MicroC.

### R1.4 — A parameter must be consumed, not just defined

Declaring a parameter and consuming it are separate acts, and in this codebase
they have drifted apart repeatedly (see the table of real cases in `CLAUDE.md`
→ "No hidden biology"). A value that is read into a local and logged — but never
used in a formula — **does nothing**, and showing it in the GUI is a lie.

Obligations, both directions:

- **When adding a parameter:** wire it into the computation, then **prove it**:
  run with a deliberately non-default value and confirm the result changes
  (or assert, in a focused test, that the value reaches the formula).
- **When exposing an existing constant:** the new parameter's default must
  reproduce the previous hardcoded behavior **exactly** (baseline results
  unchanged), *and* a non-default value must demonstrably take effect.
- **Before tuning or recommending a parameter:** grep for where it is **read**.
  If the only hits are the assignment and a log line, say so plainly — do not
  propose values for a dead knob.

```bash
# where is it READ? (not where is it assigned)
grep -rn "<param_name>" opencellcomms_engine/src opencellcomms_adapters --include='*.py'
```

### R1.5 — Logs, labels, and descriptions state the effective rule

What the simulation prints and what the GUI displays must describe **the rule
actually applied this run** — including which mode ran and where its values came
from. When a node supports more than one law (deterministic vs probabilistic,
table vs fallback), its output must name the one in effect
(e.g. `hill(conc/1.7e-05) > ran` instead of a generic `conc > thr`;
`init activation (associations): …` vs `(legacy fallback): …`). A stale
description that documents the old rule is a violation, same as stale code.

### R1.6 — The canvas is the unit of readability

A scientist reads the **canvas**: node names, node descriptions,
parameter-node labels. **They will not open dictionary editors, and they will
not read Python — assume they never go deeper than the canvas.** A mechanism
is therefore exposed only if its *existence* is announced at canvas level:

- **A law, a mode switch, or a protocol gets its own node** — or its own
  clearly-labeled parameter slot on the owning node — whose display name says
  what it does, whose description states the equation/protocol, and whose
  parameter node lists its subjects and coefficients under a self-explanatory
  label.
- **Dict tables hold tuning values of a mechanism the canvas already
  announces — never the mechanism itself.** A dict entry is free-form text:
  nothing guides which keys are legal, nothing explains the protocol, and a
  "magic key" that switches the law (e.g. `"activation": "hill"` inside a
  value dict) is invisible until someone happens to open that dictionary.
  That is hidden biology even though it is technically "in the GUI".
- **The self-audit:** describe the model out loud reading *only* what is
  visible on the canvases — node names, descriptions, parameter labels. Every
  law or mode you would have to omit, or could only discover by opening an
  editor, is a violation.

**The tell:** "unless the scientist opens the dictionary, they will not even
know this rule is enforced." *In-repo model:* the NetLogo probabilistic drug
activation is switched on by the dedicated **Hill (Probabilistic) Input
Activation** node — its first draft put the switch inside the Associations
dict as a free-form key and was rejected under this rule.

---

## R2 — Exactly one source of truth

**Every biological law, and every biological value, lives in exactly one
place.** Everything else that needs it **reads it from there**. Duplication is
how a model silently forks: two copies agree today, then one is tuned and the
other keeps deciding half the biology.

### R2.1 — One law, one implementation

A biological law (a formula, an activation rule, a fate criterion) is
implemented **once**. If two nodes need it, it becomes a **shared helper** that
both import — never a second copy, "kept in sync". Give the helper a public
name, document the law once at its definition site (with its literature/NetLogo
provenance), and let every consumer's docstring point there.

**The tell:** the same formula typed in two files, or a comment saying
"matches the formula in X". Matching is not sharing.

### R2.2 — One value, one owner

Each parameter value has exactly **one owning GUI location** — one parameter
node, one dict-table row. Every other consumer, in any phase, resolves the
value **from that owner** at run time (via config/context), and never
redeclares it.

The demanding case is **initialization vs per-step**: a function that runs once
at t=0 and a function that runs every tick often need the same threshold or
coefficient. They must both read the owning table — the init function does
*not* get its own private copy of the number. Workflow init order must make the
owner available first (in the synthesized scaffold, `__world__` setup runs
before agent creation precisely so creation-time code can read what setup
wrote).

Planner tabs follow the same rule: overrides are **sparse diffs** from the
owning parameter node, never snapshot copies of it (`validate_workflow.py`
warns on redundant copies — that warning is this rule).

### R2.3 — Fallback defaults, strictly bounded

A hardcoded fallback for a value whose owner is a table/parameter is legal
**only when all of these hold**:

1. The owner can **legitimately be absent** in a supported execution mode
   (e.g. a standalone benchmark run that has no association table) — not merely
   "might be misconfigured".
2. The fallback reproduces the **pre-existing behavior exactly** (prove it —
   bit-identical where feasible).
3. The fallback is **documented at its definition site** as a fallback, naming
   the owner it substitutes for.
4. The code **logs which source was used** when it matters (R1.5).

A fallback that fires when the owner *is* present is a bug: the owner always
wins.

### R2.4 — Two spellings of the same store are a bug until proven identical

`config.custom_parameters` vs `context['custom_parameters']`;
`config.thresholds` vs `context['thresholds']`. When a value can live under two
adjacent spellings, **verify they are the same object or that every reader
checks both in a fixed precedence order** — never assume, and never add a third
spelling. When you add a new stored value, put it in the store its consumers
already read.

### R2.5 — Documentation follows the same rule

A rule or mechanism is documented canonically in **one** document; every other
document links to it, adding at most a one-paragraph summary. Copy-pasting a
rules section into a second doc creates the same silent fork as copy-pasting a
formula. (This document is the canonical home of the readability rules;
`CLAUDE.md` holds the case law; the `/occ_*` skills carry only the pointer
block.)

---

## Verification checklist

Run this **before reporting any adapter/workflow/node work as done**. Each item
names the rule it enforces.

1. **[R1.1–R1.2] Exposure sweep.** List every biological constant, threshold,
   coefficient, and law your change touches. For each: which node/parameter
   exposes it? Anything answered "a Python constant" must be exposed or must
   qualify as an R2.3 fallback (documented, owner-absent-only).
2. **[R1.4] Consumption proof.** For every parameter added or exposed: grep
   where it is **read**; run (or focused-test) with a deliberately non-default
   value and confirm the computation changes.
3. **[R1.4] Neutrality proof.** For every previously-hardcoded value now
   exposed: defaults reproduce the old behavior exactly.
4. **[R2.1–R2.2] Duplication sweep.** Grep for the constant's value, the
   formula's distinctive terms, and the parameter's name across
   `opencellcomms_engine/src` and `opencellcomms_adapters`. Every second
   occurrence must be a *reader of the owner* or a *documented R2.3 fallback*
   — otherwise unify before finishing.
5. **[R2.3] Fallback audit.** For each fallback: does a supported mode really
   exist where the owner is absent? Is it bit-equivalent to prior behavior? Is
   the source logged?
6. **[R1.3] Structure.** `python opencellcomms_engine/scripts/validate_workflow.py
   <workflow.json>` exits 0 for every workflow touched.
7. **[R1.5] Truthful output.** Read the actual log lines / node descriptions
   your change produces: do they state the rule and source in effect?
8. **[R1.6] Canvas self-audit.** Read the touched canvases as a scientist
   would — node names, descriptions, and parameter labels only. Can you state
   every law and mode in effect without opening a dict editor or a `.py`
   file? Any mechanism discoverable only inside a dictionary must be promoted
   to its own node or labeled slot.

---

## Worked example (in-repo): the NetLogo drug-activation law

The Hill probabilistic activation of `MCT1I`/`GLUT1I` is the reference
implementation of these rules — copy this pattern.

- **The mechanism is announced on the canvas** (R1.6): a dedicated node,
  **Hill (Probabilistic) Input Activation** (`set_hill_input_activation`,
  World canvas), whose display name and description state the protocol and
  equation. Its first draft instead hid the switch as an `"activation":
  "hill"` key inside the Associations dict — technically "in the GUI", but
  invisible until someone opened the dictionary, and free-form once they did.
  That draft was rejected under R1.6 and replaced by the node.
- **The law lives once** (R2.1):
  `opencellcomms_adapters/common/functions/gene_network/apply_associations_to_inputs.py`
  defines `hill_probability()` / `resolve_hill()`, with the NetLogo provenance
  (`-ACTIVE-FROM-PATCH-16`) documented at the definition site. Nothing else
  re-implements the formula.
- **Each value has one owner** (R2.2): the hill node's **Hill-Activated
  Inputs** table owns *which* inputs are probabilistic and their
  `hill_max`/`hill_exponent` (explicit `0.85`/`1.0` in the workflow — visible,
  not silent code defaults, R1.2). The **threshold** stays owned by the
  input's row in the **Associations (Dict)** table on `Setup Associations` —
  the hill node deliberately does not repeat it.
- **Every consumer reads the owners** (R2.2): the per-step
  `apply_associations_to_inputs` and the t=0 activation in
  `initialize_netlogo_gene_networks.py` (`_drug_activation_law`) both resolve
  the same two stores at run time; neither keeps a private copy.
- **The fallback is bounded** (R2.3): only when *neither owner knows the
  input* (the standalone benchmark, which has no tables) does init fall back
  to the legacy values — verified bit-identical to the old behavior — and the
  log says which source was used: `init activation (associations): …` vs
  `(legacy fallback): …` (R1.5).
- **Consumption was proven** (R1.4): a run with `hill_max: 0.4` changed the ON
  fraction from ~0.85 to ~0.39; explicit `0.85`/`1.0` matched the defaults
  exactly; removing the node reverted the input to the deterministic test.

---

## Anti-pattern index (the tells)

| You catch yourself… | Rule | Required fix |
|---|---|---|
| explaining in prose where a constant lives and how to edit Python to change it | R1.2 | expose it as a node parameter |
| writing a constant into a helper because "it matches the reference paper" | R1.2 | parameter with the reference value as its default |
| adding a parameter and moving on once it "shows up in the GUI" | R1.4 | grep reads + non-default run proof |
| tuning/recommending a value without checking where it is read | R1.4 | consumption check first; call out dead knobs plainly |
| typing a formula that already exists in another file | R2.1 | import the shared helper (make it public if needed) |
| giving an init/setup function its own copy of a threshold the step function owns | R2.2 | resolve from the owning table at run time |
| copying canvas values into a planner tab override wholesale | R2.2 | keep overrides as sparse diffs |
| adding a "safe default" fallback for a table that is always present | R2.3 | delete the fallback; fail loudly instead |
| writing to `context['X']` when consumers read `config.X` (or vice versa) | R2.4 | write to the store the consumers read |
| pasting a rules/mechanism section into a second document | R2.5 | one-paragraph summary + link |
| leaving a log line/description that describes the previous rule | R1.5 | make output name the effective rule and source |
| parking a behavior where no GUI tab can reach it | R1.3 | home it per the CLAUDE.md homing rules; validator must pass |
| burying a law switch / mode flag as a free-form key inside a dict entry | R1.6 | dedicated node (or labeled slot) whose name announces the mechanism |
| relying on the scientist opening a dict/editor to learn a mechanism exists | R1.6 | canvas-level node name + description state the protocol |

---

## Adding rules

This section is for maintainers extending the contract (rules are added here
**and nowhere else**):

1. Append a new top-level rule (`R3`, `R4`, …) or sub-rule (`R1.6`, `R2.6`, …)
   — **never renumber** existing IDs; other documents and commit messages cite
   them.
2. Give it the same shape: a bold one-sentence statement, the rationale, the
   *tell*, and — where possible — an in-repo model to copy.
3. Add its check to the [Verification checklist](#verification-checklist) and
   its tell to the [Anti-pattern index](#anti-pattern-index-the-tells).
4. If it is mechanically checkable, extend
   `opencellcomms_engine/scripts/validate_workflow.py` and note the coverage in
   [How to use this document](#how-to-use-this-document).
5. Do **not** copy the rule's text into `CLAUDE.md` or the skills — they carry
   a pointer; case law goes in `CLAUDE.md` when a real violation is found.

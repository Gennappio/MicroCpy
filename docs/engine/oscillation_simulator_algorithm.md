# Oscillation Simulator — Detailed Algorithm Description

**File:** `opencellcomms_engine/benchmarks/gene_network_workflow_oscillation_simulator.py`

This document describes, step by step, exactly what the oscillation simulator
does — from loading files through every tick of the simulation.

---

## 1. LOADING PHASE

### 1.1 Load the Gene Network (`.bnd` file)

The simulator reads a Boolean Network Description file (e.g. `jaya_microc.bnd`).
Each node in the file has:

- A **name** (e.g. `ERK`, `Apoptosis`, `Oxygen_supply`)
- A **logic rule** (e.g. `logic = (!ERK & p53 & FOXO3 & !BCL2);`)

The loader classifies each node into one of three kinds:

| Kind | How identified | Examples |
|---|---|---|
| **Input** | Has `rate_up = 0` and `rate_down = 0`, or its logic rule is just itself (e.g. `logic = (Oxygen_supply)`) | `Oxygen_supply`, `Glucose_supply`, `MCT1_stimulus`, `EGFR_stimulus`, `GLUT1I`, `MCT1I`, ... |
| **Output-Fate** | Name is one of `{Apoptosis, Proliferation, Growth_Arrest, Necrosis}` | `Apoptosis`, `Proliferation`, `Growth_Arrest`, `Necrosis` |
| **Gene** | Everything else | `ERK`, `p53`, `MYC`, `AKT`, `MEK1_2`, ... |

After loading, the simulator builds a **directed graph**: for each gene/fate node,
it finds which nodes appear in its logic rule and creates links from those nodes
to this node.  For example, if `Apoptosis` has rule `(!ERK & p53 & FOXO3 & !BCL2)`,
then directed links are created: `ERK → Apoptosis`, `p53 → Apoptosis`,
`FOXO3 → Apoptosis`, `BCL2 → Apoptosis`.

Result: a graph with ~106 nodes and ~169 directed links.

### 1.2 Load Input States (`.txt` file)

The input file lists the initial ON/OFF state of each input node:

```
Oxygen_supply=ON
Glucose_supply=ON
MCT1_stimulus=ON
cMET_stimulus=OFF
Growth_Inhibitor=OFF
...
```

Two special nodes (`GLUT1I` and `MCT1I`) can also accept a numeric concentration
value.  If a number is provided, they use a Hill-function comparison against the
cell's random threshold (see Section 2.2).  If ON/OFF is provided, they behave
like normal inputs.

---

## 2. CELL CREATION

### 2.1 Cell Structure

Each cell is an independent copy of the gene network.  It owns:

| Attribute | Description |
|---|---|
| `nodes` | A dictionary of all 106 nodes, each with its own `active` (True/False) state. This is the cell's private copy — changing one cell's ERK does not affect another's. |
| `last_node` | The node where the random walk cursor currently sits (initially a random Input node). |
| `fate` | The cell's current fate: `None` (no fate), `"Apoptosis"`, `"Proliferation"`, `"Growth_Arrest"`, or `"Necrosis"`. Starts as `None`. |
| `cell_ran1` | A random float in [0, 1), fixed at birth. Used for MCT1I probabilistic input. |
| `cell_ran2` | A random float in [0, 1), fixed at birth. Used for GLUT1I probabilistic input. |
| `age` | Incremented by 1.0 each tick. Reset to 0.0 after proliferation. |
| `growth_arrest_cycle` | Countdown from 3 to 0 during Growth Arrest. |

### 2.2 Cell Initialization (`reset`)

When a cell is created (or reset after division), the following happens:

1. **Input nodes**: left unchanged (they will be set by `set_input_states`).
2. **Fate nodes** (`Apoptosis`, `Proliferation`, `Growth_Arrest`, `Necrosis`): all set to `active = False`.
3. **Gene nodes** (everything else): each independently set to `True` or `False` with 50/50 probability. This random initialization is critical — it means every cell starts with a unique internal state.
4. **Walk cursor** (`last_node`): set to a random Input node.
5. **Fate**: set to `None`.
6. **`cell_ran1`, `cell_ran2`**: each set to a new `random()` in [0, 1).
7. **Age**: set to 0.

### 2.3 Applying Input States (`set_input_states`)

After reset, the cell's input nodes are set from the input file:

- **Normal inputs** (e.g. `Oxygen_supply=ON`): the node is simply set to `True` or `False`.
- **Probabilistic inputs** (`MCT1I`, `GLUT1I`): if a concentration was provided, a Hill function is computed:
  ```
  hill = 0.85 * (1 - 1 / (1 + concentration))
  ```
  Then `MCT1I.active = (hill > cell_ran1)` and `GLUT1I.active = (hill > cell_ran2)`.
  Since `cell_ran1`/`cell_ran2` differ per cell, the same concentration produces different results across cells.

### 2.4 Initial Population

The simulator creates N cells (e.g. 100), each independently initialized as
described above.  All cells see the same initial input states but have different
random gene states, different walk cursors, and different `cell_ran1`/`cell_ran2`.

---

## 3. SIMULATION PARAMETERS

Before the main loop starts, one global parameter is drawn:

- **`proliferation_delay`**: a single random integer from 1 to `intercellular_step` (e.g. 1 to 100).  This is the tick offset before the first proliferation/growth-arrest check.  It is **global** — all cells share the same delay.  This matches NetLogo's `the-proliferation-delay`.

Default timing parameters:

| Parameter | Default | Meaning |
|---|---|---|
| `total_ticks` | 7000 | Total simulation time |
| `intercellular_step` | 100 | Ticks between proliferation/GA checks |
| `diffusion_step` | 250 | Ticks between input refreshes |
| `oscillation_period` | 500 | Full ON/OFF cycle for oscillating inputs |

---

## 4. MAIN LOOP — What Happens Each Tick

The simulation loops from `tick = 1` to `tick = total_ticks`.  Each tick executes
the following steps **in this exact order**:

### STEP 1: APOPTOSIS CHECK (every tick)

```
For each cell in the population:
    If cell.fate == "Apoptosis":
        Remove cell from the population (it dies)
        Increment death counter
```

This runs **every single tick**.  A cell that acquired `fate = "Apoptosis"` during
the previous tick's graph walk (Step 3) dies here.  There is a 1-tick delay
between acquiring the Apoptosis fate and dying (the cell walks on tick N, gets
Apoptosis, dies at the start of tick N+1).

This matches NetLogo's `-APOPTOSIS-NECROSIS-100` which uses `do-after(1), do-every(the-apoptosis-step)` where `the-apoptosis-step = 1`.

### STEP 2: INPUT REFRESH (every `diffusion_step` ticks)

This step runs only when `tick % diffusion_step == 0` (e.g. ticks 250, 500, 750, ...).

#### 2a. Compute Oscillation State (if `--oscillation` is enabled)

The simulator maintains an `_effective_inputs` dictionary — a mutable copy of the
original input states.  At each diffusion step, it updates this dictionary:

**Oscillating inputs** (`MCT1_stimulus` by default):

```
half = oscillation_period // 2     (e.g. 250)
phase = tick % oscillation_period  (e.g. tick 500 → phase 0, tick 750 → phase 250)

If phase < half:
    MCT1_stimulus = ON    (first half of the period)
Else:
    MCT1_stimulus = OFF   (second half of the period)
```

With `oscillation_period = 500`, this means:
- Ticks 0–249: MCT1_stimulus = ON
- Ticks 250–499: MCT1_stimulus = OFF
- Ticks 500–749: MCT1_stimulus = ON
- Ticks 750–999: MCT1_stimulus = OFF
- ... and so on

**Delayed inputs** (`cMET_stimulus` by default):

```
If tick >= diffusion_step:
    cMET_stimulus = ON
```

This turns ON at the first diffusion step (tick 250) and stays ON forever.
In NetLogo, this happens because HGF (growth factor) diffuses into the domain
only after the first diffusion solve.

#### 2b. Apply Inputs to All Cells

```
For each cell:
    If --ran-refresh is enabled:
        cell.cell_ran1 = new random()
        cell.cell_ran2 = new random()
    Apply _effective_inputs to cell's input nodes
```

For normal inputs, this sets the node's `active` directly.  For probabilistic
inputs (MCT1I, GLUT1I), it re-evaluates `hill(concentration) > cell_ran`.

**Why this matters:** changing an input node's state mid-simulation alters what
downstream gene rules evaluate to.  For example, if `MCT1_stimulus` flips from
ON to OFF, then `MCT1` (which depends on `MCT1_stimulus`) may change, which
affects `mitoATP`, which affects `ATP_Production_Rate`, which affects the
`Proliferation` fate rule.  This cascade is what breaks Boolean attractors.

### STEP 3: ONE GRAPH-WALK STEP (every tick)

This is the core of the gene network update.  **Every living cell** performs
exactly one step of a random walk through the gene network graph.

#### 3a. Gating: Should the Cell Walk?

```
If reversible mode:
    If cell.fate == "Necrosis": SKIP (do not walk)
    Otherwise: WALK (even if cell has Apoptosis, Proliferation, or Growth_Arrest)
If non-reversible mode:
    If cell.fate is not None: SKIP (any fate stops the walk)
    Otherwise: WALK
```

In reversible mode, a cell with `fate = "Proliferation"` **keeps walking**.  It
can visit other fate nodes and have its fate overwritten.  Only Necrosis is
terminal.

#### 3b. The Walk Step (`_downstream_change`)

```
current_node = cell.last_node   (where the cursor is)

If current_node has no outgoing links:
    Jump cursor to a random Input node
    DONE

Pick a random outgoing link → target_node
Save cell.fate as fate_before_this_step

If target_node has a Boolean rule:
    Evaluate the rule using ALL current node states of this cell
    new_state = result of evaluation (True or False)
    If target_node.active != new_state:
        target_node.active = new_state
    (If they are the same, nothing changes)

If target_node is an Output-Fate node:
    FATE HANDLING (see below)
    Reset target_node.active = False    (transient trigger)
    Jump cursor to a random Input node
Else:
    Move cursor to target_node
```

#### 3c. Fate Handling (when the walk visits a fate node)

This is the most critical part of the algorithm.  It happens inside the walk
step, only when `target_node.kind == "Output-Fate"`:

```
If target_node.active == True:
    cell.fate = target_node.name
    (e.g. cell.fate = "Apoptosis")
    The LAST fate to fire wins — it overwrites any previous fate.

If target_node.active == False AND target_node.name == fate_before_this_step:
    cell.fate = None
    This is the REVERT mechanism: if the cell's current fate was "Apoptosis"
    and the walk visits the Apoptosis node and the rule evaluates to False,
    the fate is cleared back to None.

target_node.active = False   (always reset after visiting)
```

**Example sequence in reversible mode:**

```
Tick 100: Walk visits Apoptosis node → rule evaluates True → cell.fate = "Apoptosis"
Tick 101: Walk visits ERK node → ERK flips state → nothing special
Tick 102: Walk visits Proliferation node → rule evaluates True → cell.fate = "Proliferation" (overwrites Apoptosis!)
Tick 103: Walk visits Apoptosis node → rule evaluates False → fate was "Proliferation" not "Apoptosis" → NO revert
Tick 104: Walk visits Proliferation node → rule evaluates False → fate WAS "Proliferation" → REVERT → cell.fate = None
```

**Key point:** there is NO priority between fates.  The outcome depends entirely
on which fate node the random walk visits last and what the Boolean rule evaluates
to at that moment.  However, Apoptosis has a **timing advantage** because it is
checked every tick (Step 1), while Proliferation is only checked every 100 ticks
(Step 4).

### STEP 4: PROLIFERATION / GROWTH-ARREST CHECK (periodic)

This runs when `tick >= proliferation_delay AND (tick - proliferation_delay) % intercellular_step == 0`.

For example, with `proliferation_delay = 41` and `intercellular_step = 100`:
runs at ticks 41, 141, 241, 341, ...

```
For each cell in the population:
    If cell.fate == "Proliferation":
        PROLIFERATE (see below)
    Else if cell.fate == "Growth_Arrest":
        GROWTH ARREST CYCLE (see below)
```

#### 4a. Proliferation

When a cell has `fate = "Proliferation"` at the check boundary:

**Reset the parent cell:**
```
cell.fate = None
cell.age = 0.0
cell.cell_ran1 = new random()
cell.cell_ran2 = new random()
Apply current _effective_inputs to cell
Set all 4 fate nodes (Apoptosis, Proliferation, Growth_Arrest, Necrosis) to active=False
```

The parent cell is NOT killed — it is reset and continues walking from wherever
its cursor was.  It has new random thresholds, fresh age, and no fate.  But its
**internal gene states are preserved** (ERK, p53, MYC, etc. keep their current
values).  Only the fate nodes and randoms are reset.

**Create a daughter cell:**
```
daughter = new Cell
daughter.reset(random_init=True)   (all genes randomized 50/50, new cursor, new ran1/ran2)
daughter.set_input_states(_effective_inputs)
Add daughter to population
```

The daughter starts completely fresh — independent random gene states, independent
walk cursor, independent randoms.  She immediately begins walking on the next tick.

#### 4b. Growth Arrest Cycle

When a cell has `fate = "Growth_Arrest"` at the check boundary:

```
If growth_arrest_cycle == 0:
    growth_arrest_cycle = 3    (start the countdown)
growth_arrest_cycle -= 1
If growth_arrest_cycle <= 0:
    cell.fate = None           (release from growth arrest)
    growth_arrest_cycle = 0
```

This means a cell stays in Growth Arrest for 3 consecutive intercellular check
periods (300 ticks), then its fate is cleared and it resumes walking.

### STEP 5: AGE ALL CELLS (every tick)

```
For each cell (including newly created daughters):
    cell.age += 1.0
```

### STEP 6: PERIODIC REPORTING (every `intercellular_step` ticks)

At ticks 100, 200, 300, ..., the simulator prints a summary line:

```
Tick 1400: Pop=126 (+11 births, -4 deaths) fates={'None': 119, 'Proliferation': 7}
```

---

## 5. HOW THE OSCILLATION BREAKS BOOLEAN ATTRACTORS

Without oscillation, the gene network settles into **Boolean attractors** —
stable states where every gene rule evaluates to its current value, so the walk
never changes anything.  Typical attractor time: 1000–2000 ticks.

The oscillation breaks this by periodically flipping `MCT1_stimulus` from ON to
OFF (and back).  Here is the cascade:

```
MCT1_stimulus ON → OFF
    ↓
MCT1 (depends on MCT1_stimulus) may flip
    ↓
mitoATP (depends on MCT1) may flip
    ↓
ATP_Production_Rate (depends on mitoATP) may flip
    ↓
Proliferation rule: (!p21 & MYC & p70 & !Growth_Inhibitor & ATP_Production_Rate)
    → Proliferation may fire or revert
    ↓
Also: other genes downstream of MCT1 may change (e.g. Lactate-related pathways)
    → potentially affecting p53, FOXO3, BCL2 through indirect paths
    → Apoptosis rule: (!ERK & p53 & FOXO3 & !BCL2) may fire or revert
```

Each time MCT1_stimulus toggles, some cells that were in an attractor get kicked
out.  Their gene states start evolving again, potentially reaching new fate nodes.
New daughters also start with random states, adding variety.

The `cMET_stimulus` delayed activation (ON after tick 250) adds another
perturbation by turning on the cMET/HGF signalling pathway, which feeds into
GRB2 → SOS → RAS → RAF → MEK → ERK, broadly activating survival signalling.

---

## 6. SUMMARY OF ALL TIMERS

| What | When | Period |
|---|---|---|
| Apoptosis death check | Every tick | 1 tick |
| Input refresh + oscillation | `tick % 250 == 0` | 250 ticks |
| One graph-walk step | Every tick | 1 tick |
| Proliferation/GA check | `tick >= delay AND (tick-delay) % 100 == 0` | 100 ticks |
| Cell ageing | Every tick | 1 tick |
| MCT1_stimulus ON→OFF toggle | With period 500 ticks (computed at diffusion steps) | 500 ticks |
| cMET_stimulus activation | Once, at tick 250 | one-shot |

---

## 7. PSEUDOCODE — COMPLETE MAIN LOOP

```
LOAD bnd_file → nodes, links
LOAD input_file → input_states
COPY input_states → _effective_inputs

CREATE initial_population cells, each:
    randomize gene states (50/50)
    set fate = None
    set ran1, ran2 = random()
    apply _effective_inputs to input nodes

proliferation_delay = random(1, intercellular_step)

FOR tick = 1 TO total_ticks:

    ── STEP 1: APOPTOSIS ──
    REMOVE all cells where cell.fate == "Apoptosis"

    ── STEP 2: INPUT REFRESH (every diffusion_step ticks) ──
    IF tick % diffusion_step == 0:
        IF oscillation enabled:
            phase = tick % oscillation_period
            IF phase < oscillation_period / 2:
                _effective_inputs["MCT1_stimulus"] = ON
            ELSE:
                _effective_inputs["MCT1_stimulus"] = OFF
            IF tick >= diffusion_step:
                _effective_inputs["cMET_stimulus"] = ON

        FOR each cell:
            IF ran_refresh enabled:
                cell.ran1 = random()
                cell.ran2 = random()
            APPLY _effective_inputs to cell's input nodes

    ── STEP 3: GRAPH WALK (one step per cell) ──
    FOR each cell:
        IF reversible AND cell.fate == "Necrosis": SKIP
        IF non-reversible AND cell.fate != None: SKIP

        current = cell.last_node
        IF current has no outgoing links:
            cell.last_node = random Input node
            CONTINUE

        target = random outgoing neighbor of current
        fate_before = cell.fate

        IF target has a Boolean rule:
            new_state = EVALUATE rule using cell's current node states
            IF target.active != new_state:
                target.active = new_state

        IF target is a Fate node:
            IF target.active == True:
                cell.fate = target.name
            IF target.active == False AND target.name == fate_before:
                cell.fate = None      ← REVERT
            target.active = False     ← transient reset
            cell.last_node = random Input node
        ELSE:
            cell.last_node = target

    ── STEP 4: PROLIFERATION / GROWTH ARREST (periodic) ──
    IF tick >= proliferation_delay AND (tick - proliferation_delay) % intercellular_step == 0:
        FOR each cell:
            IF cell.fate == "Proliferation":
                cell.fate = None
                cell.age = 0
                cell.ran1 = random()
                cell.ran2 = random()
                APPLY _effective_inputs to cell
                SET all fate nodes active = False
                CREATE daughter (fully randomized, fresh)
                APPLY _effective_inputs to daughter
                ADD daughter to population

            ELSE IF cell.fate == "Growth_Arrest":
                IF growth_arrest_cycle == 0: growth_arrest_cycle = 3
                growth_arrest_cycle -= 1
                IF growth_arrest_cycle <= 0:
                    cell.fate = None
                    growth_arrest_cycle = 0

    ── STEP 5: AGE ──
    FOR each cell: cell.age += 1

    ── STEP 6: REPORT (every intercellular_step ticks) ──
    IF tick % intercellular_step == 0:
        PRINT population count, births, deaths, fate distribution
```

---

## 8. KEY DIFFERENCES FROM THE FAITHFUL SIMULATOR

| Aspect | Faithful (`gene_network_workflow_simulator.py`) | Oscillation (`gene_network_workflow_oscillation_simulator.py`) |
|---|---|---|
| `MCT1_stimulus` | Fixed at its initial value (ON or OFF) forever | Toggles ON/OFF every 250 ticks (with period 500) |
| `cMET_stimulus` | Fixed at its initial value forever | Turns ON at tick 250 and stays ON |
| `cell_ran1`/`cell_ran2` | Fixed per cell lifetime | Optionally re-randomized every 250 ticks (`--ran-refresh`) |
| Long-term behaviour | Stagnation in Boolean attractors (~2000 ticks) | Sustained activity (births + deaths continue indefinitely) |
| NetLogo fidelity | Exact match of gene-walk algorithm | Approximation of diffusion-driven perturbation |

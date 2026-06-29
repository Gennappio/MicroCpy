# First Steps with OpenCellComms

A hands-on, learn-by-doing introduction. You don't need to read the whole
codebase — just follow the exercises in order. Each one is small, takes a few
minutes, and builds on the last. By the end you'll be able to load, run, modify,
extend, and share a simulation.

> **Who this is for:** biologists and biologist-developers who want to *test a
> biological hypothesis* with an agent-based model, without first becoming a
> software engineer. Most of what you do happens in the visual GUI.

---

## 0. The mental model (read this once, 3 minutes)

OpenCellComms runs **agent-based models (ABM)** of biological systems. Three
ideas are enough to start:

1. **Agents** — individual cells. Each has a position, a phenotype
   (`proliferating`, `apoptotic`, `necrotic`, `growth_arrested`, …) and,
   optionally, its own gene network.
2. **Environment** — the space the cells live in, and the **substances**
   (oxygen, glucose, …) that diffuse through it as chemical gradients.
3. **The Scheduler** — the main loop. Every step, it runs a list of
   **behaviors** (small rules) on the agents and the environment: update genes,
   decide cell fate, divide, diffuse, and so on.

A whole experiment is a **workflow**: one JSON file describing the agents, the
environment, the init steps, and the scheduler loop. Workflows are built out of
reusable **subworkflows** (called *behaviors* in the GUI), and each behavior is
a small ordered chain of **functions** (Python). You design all of this
visually; the JSON is generated for you.

```
 Workflow
 ├─ Initialization   → runs ONCE at t=0 (place cells, set up substances)
 └─ Scheduler loop   → repeats N steps:
        ├─ gene_update     (a behavior = chain of functions)
        ├─ fate_update     (a behavior)
        ├─ division        (a behavior)
        └─ diffusion_step  (a behavior)
```

Keep this picture in mind; the GUI tabs map directly onto it.

---

## 1. Install and launch (once)

From the project root, install once, then launch.

**macOS / Linux:**
```bash
./install.sh      # one-time: creates a venv, installs the engine + GUI deps
./run.sh          # starts everything
```

**Windows:**
```batch
install.bat       :: one-time: creates a venv, installs the engine + GUI deps
run.bat           :: starts everything
```

Either launcher starts two servers and prints their URLs:

- **Frontend (the GUI):** http://localhost:3000  ← open this in your browser
- **Backend (the engine):** http://localhost:5001 ← runs the Python simulation

Leave the launcher running in its terminal. Open the Frontend URL. Stop
everything later with `Ctrl+C` in that terminal (on Windows, close the two
server windows).

> Tip: `./run.sh -v` streams backend activity to the terminal — useful when a
> run misbehaves.
>
> **Windows note:** wherever this guide shows `./run.sh` or `./install.sh`, use
> `run.bat` / `install.bat` instead.

**Prefer Docker?** With [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed, one command runs the whole stack on any OS, with no local Python or Node setup:

```bash
docker compose up --build      # then open http://localhost:3000
```

See [docs/INSTALL.md](docs/INSTALL.md#run-with-docker-any-os) for details and caveats.

---

## Exercise 1 — Run the example and watch it (10 min)

**Goal:** see a complete simulation run end-to-end before changing anything.

1. In the GUI top bar, click **Import Project**.
2. Open `opencellcomms_adapters/MicroC/workflows/microc.json`. This is the
   reference model: a small tumour spheroid with oxygen diffusion, a gene
   network, cell-fate decisions, and division.
3. Find the **console** panel (it has a **Run** button). Click **Run**.
4. Watch the log stream. When it finishes, open the **Results** tab to see the
   plots and exported data.

**What you just saw:** cells were placed (initialization), then the scheduler
looped for a number of steps, updating genes, fate, and division each step while
oxygen diffused.

✅ *Success check:* the run completes without an error and the Results tab shows
output. If it fails, jump to **Troubleshooting** at the bottom.

---

## Exercise 2 — Tour the tabs (10 min)

**Goal:** map the GUI onto the mental model from §0. Don't change anything yet —
just look.

With `microc.json` loaded, click through the top tabs in order:

| Tab | What lives here |
|---|---|
| **Agents** | The cell kinds (here: `tumor_cell`), their *init* behavior (`tumor_cell_init`) and their per-step behaviors (`gene_update`, `fate_update`, `division`). |
| **Environment** | Environment setup and diffusion behaviors (`environment_init`, `diffusion_step`). |
| **Initialization** | The *order* of things that run **once** at the start. |
| **Scheduler** | The **main loop**: which behaviors run each step, and **how many steps** (the "Simulation Steps" parameter). |
| **Planner** | Parameter values + batch runs (Exercise 4). |
| **Processing** | Post-simulation behaviors (plots, summaries — e.g. `iteration_plots`, `final_summary`). |
| **Results** | Output plots and data from the last run. |

On any canvas, **click a node** to inspect it. Function nodes show their
parameters; the controller node (the one the chain starts from) shows
stage-level settings.

✅ *Success check:* you can point at where the number of simulation steps is
set (Scheduler tab) and where cells are first placed (Agents → `tumor_cell_init`).

---

## Exercise 3 — Change one parameter and re-run (10 min)

**Goal:** prove to yourself that editing → running → seeing a different result
works. We'll change the loop length, the simplest possible knob.

1. Go to the **Scheduler** tab.
2. Find the **Simulation Steps** parameter node (it's wired into the
   scheduler's controller). Change its value — e.g. from its current value to a
   smaller number like `5` so the run is quick.
3. Click **Run** again.
4. Compare the log / Results to Exercise 1 — fewer steps, shorter simulation.

Now try a *biological* knob:

5. Go to **Agents → tumor_cell_init** (or **Environment**). Click a function
   node and open a **parameter node** connected to it. Change a value (a cell
   count, a substance level, a threshold).
6. Re-run and look at the Results.

**The lesson:** parameters are exposed as small **parameter nodes** wired into
function nodes. You change biology by changing these — no code.

✅ *Success check:* the run length or the result visibly changes after your edit.

---

## Exercise 4 — Batch runs with the Planner (10 min)

**Goal:** run the *same* model with *different* parameter sets, side by side —
the everyday tool for a parameter sweep or a hypothesis test.

1. Open the **Planner** tab. Click **+ New** to create a configuration tab
   (e.g. "Low oxygen"). It snapshots the current parameter values.
2. Edit one or more values in that configuration (e.g. lower a substance level,
   or change Simulation Steps).
3. Click **+ New** again for a second configuration ("High oxygen") and set a
   different value.
4. Make sure both configurations are **enabled** (the eye icon), then press
   **Run**. Enabled configurations run **sequentially**.

**The lesson:** the Planner lets you hold several "what if?" scenarios at once
without editing the canvas each time. This is how you compare conditions.

✅ *Success check:* the console runs each enabled configuration in turn.

---

## Exercise 5 — Read a behavior, understand `context` (15 min)

**Goal:** look *inside* a function and connect the visual node to the Python
that runs. This is the bridge between "biologist" and "developer".

1. Go to **Agents → fate_update** (cell-fate decisions). Click a function node.
2. View its source (the parameter/code panel shows it, or use the code viewer).
   Notice the shape: every function receives one thing — a **`context`** — and
   loops over cells.

A typical rule looks like this (from the project's own guide):

```python
# Kill cells when oxygen drops below a threshold
for cell in context['population'].cells:
    x, y = cell.position[0], cell.position[1]
    oxygen = context['simulator'].get_substance_concentration('oxygen', x, y)
    if oxygen < necrosis_threshold:
        cell.state.phenotype = 'necrotic'
```

Everything you need is reachable from `context`:

| You want | Code |
|---|---|
| every cell | `for cell in context['population'].cells:` |
| substance at a cell | `context['simulator'].get_substance_concentration('oxygen', x, y)` |
| a gene's state | `context['gene_networks'][cell.id].nodes['GeneName'].current_state` |
| make a cell die | `cell.state.phenotype = 'apoptotic'` |
| make a cell divide | `cell.state.phenotype = 'proliferating'` |

(The full table and more recipes are in `CLAUDE.md` → *Biologist's Guide* and in
`docs/CREATING_FUNCTIONS.md`.)

**The lesson:** a "behavior" you see on the canvas is just an ordered chain of
these small, readable functions. Nothing is hidden.

✅ *Success check:* you can read one function node and say, in one sentence, what
biological rule it implements.

---

## Exercise 6 — Write your own rule (20 min)

**Goal:** add a new biological rule and wire it into the model.

1. Open a behavior canvas that hosts functions (e.g. **Agents → fate_update**).
2. In the **Library** panel (left), click **New Function**. Give it a name and
   declare its parameters. (The Python file isn't written yet — it's *staged*.)
3. Drag your new function from the Library onto the canvas and connect it into
   the behavior chain (controller → … → your function).
4. Open it and fill in the rule using the `context` patterns from Exercise 5.
5. Click **Export Behavior** (top-right of the canvas). You'll be asked **where
   to save** — pick a folder. This writes:
   - the function's `.py` file, and
   - the behavior's `.subworkflow.json` structure file.
6. **Restart the backend** so the engine registers your new function:
   `Ctrl+C` in the `run.sh` terminal, then `./run.sh` again. Now your function
   appears (no longer greyed out) in the Library and can be run.
7. Re-import your project if needed, then **Run**.

> Why the restart? A newly written function only becomes runnable once the
> Python engine has imported and registered it. Until then the palette shows it
> greyed/undraggable — that's expected, not an error.

**The lesson:** the loop is *design visually → Export Behavior → restart →
run*. Generic, reusable functions belong in the engine; experiment-specific
ones (hardcoded gene names, thresholds) belong in an adapter — see `CLAUDE.md`
→ *Adding a new function*.

✅ *Success check:* your function runs as part of the simulation and influences
the result.

---

## Exercise 7 — Run from the command line (10 min)

**Goal:** once a workflow is designed and validated in the GUI, run it
headless — for longer runs, servers, or scripting.

From `opencellcomms_engine/`:

```bash
python run_workflow.py --workflow ../opencellcomms_adapters/MicroC/workflows/microc.json
```

The same workflow JSON the GUI produces is what the CLI consumes. The GUI's
console also has a **"Run from terminal"** helper that shows you the exact
command for the currently loaded project.

**The lesson:** GUI and CLI are two front-ends over the *same* engine and the
*same* workflow file. Prototype and understand in the GUI; run at scale on the
CLI.

✅ *Success check:* the CLI run produces the same kind of output as the GUI run.

---

## Where to go next

You now know the full loop. To go deeper:

- `CLAUDE.md` — the **Biologist's Guide** (copy-paste recipes, the `context`
  reference, biology-term → code table) and the project conventions.
- `docs/engine/GETTING_STARTED.md` — engine tutorial.
- `docs/CREATING_FUNCTIONS.md` — writing functions properly.
- `docs/GENE_NETWORK_GUIDE.md` — how per-cell Boolean gene networks work.
- `docs/USAGE.md`, `docs/WORKFLOW_STRUCTURE.md` — the workflow format in detail.
- `docs/SHARING_GUIDE.md` — sharing a model with collaborators.

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| GUI won't open at :3000 | `run.sh` not running, or `install.sh` not run yet. |
| A new function stays greyed out in the Library | The backend hasn't registered it. Restart: `Ctrl+C` then `./run.sh`. |
| Export fails with *"references unknown node ID"* | A deleted node left a stale reference — re-importing the project clears it; this case is now handled on export. |
| Run errors immediately | Re-run `./run.sh -v` to see backend logs; check that the workflow imported fully. |
| Want to reset | Re-import the original `microc.json` to get back to a known-good state. |

> **Habit to build:** design and *understand* a mechanism in the GUI first.
> Once it's tested and validated, run it from the CLI. The goal of the platform
> is to make biological hypotheses easy to build, read, share, and verify.

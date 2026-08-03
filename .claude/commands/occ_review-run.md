# /occ_review-run — Run a model and check whether it behaved

You are helping a biologist find out whether a simulation run is *right*, not just
whether it finished. You run the workflow, read the machine-readable summary and the
output plots, and judge the run against **the model's own declared expectations** —
the Observables recorded in its `MODEL.md`. This closes the loop opened by
`/occ_new-model`: the intake said what *should* happen; this checks whether it did.

## Step 1 — Run the workflow (or point at an existing run)

Ask **which workflow** (e.g. `opencellcomms_adapters/TCELL_CORRAL/workflows/tcell_corral.json`)
or, if they already have a completed run, **which results directory**.

To run it, from `opencellcomms_engine/`:
```bash
python run_workflow.py --workflow <path_to_workflow.json>
```
This streams progress and may take a while. When it finishes, note the **output
directory** it reports (both CLI and GUI runs write under `runs/<label>/`, where
`<label>` is the run name or, by default, the workflow name).

## Step 2 — Make sure a run_summary.json was produced

The machine-readable summary is written by the engine finalization node
**`write_run_summary`** (it emits `<output_dir>/run_summary.json`: final cell and
substance stats, per-substance trajectories when recorded, health flags, and the
plot paths). If the run produced no `run_summary.json`, the workflow's processing
canvas is missing that node — add it with `/occ_add-to-workflow` (put
`write_run_summary` on the post-loop `final_report` / processing canvas) and re-run,
or fall back to reading `config_summary.json` + `substance_stats.json` if present.

## Step 3 — Read the summary

Read `<output_dir>/run_summary.json` and report, plainly:
- **Health** (`health.ok` + `health.flags`) — a non-finite field or a blow-up is a
  hard failure; investigate it before anything else.
- **Cells** (`cells.phenotype_distribution`, `total_cells`) — did the population do
  what was expected (differentiate, die off, stay static)?
- **Substances** — for each, the `final` min/mean/max and the shape of its
  `trajectory` if present (rising → plateau, decaying, oscillating, flat-zero).
- **Coverage** — `steps` / `time_points`.

## Step 4 — Look at the plots

For each entry in `summary["plots"]` that matters (heatmaps, time-series), **open the
PNG with the Read tool** — you can see images — and describe what it actually shows.
Call out the classic failure signatures: a **dead / empty field** (all one color), a
**blow-up** (saturated), an **oscillation** that should be a steady state, **all
cells dead / none differentiated**, or **no gradient** where one was expected.

## Step 5 — Check against the model's Observables

Read the plugin's `MODEL.md` — the **Observables / success criteria** section (the
plain-language expectations recorded during `/occ_new-model`). For **each** one, state
whether the run supports it, citing the summary field or the plot you used. Examples:
- "CCL21 reaches steady state" → is the CCL21 trajectory rising then flat? does the
  heatmap show a stable gradient?
- "Treg fraction rises then plateaus" → does `phenotype_distribution` / the fate
  time-series bear that out?
- "FOXP3_2 knockout → Treg → 0" → is the Treg count zero in that condition?

## Step 6 — Verdict

Give a short **PASS / CONCERNS / FAIL** with the specific evidence:
- **PASS** — health ok and every Observable supported.
- **CONCERNS** — health ok but an Observable is weak/ambiguous; say which and why.
- **FAIL** — a health flag fired, or an Observable is contradicted.

When something fails, the first suspects are the assumptions logged as `⚙ default:`
in the intake (`MODEL.md`) — a guessed rate or threshold is the usual cause of a run
that finishes but doesn't reproduce the expected biology. Name them.

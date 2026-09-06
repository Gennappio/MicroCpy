# Replication and reproducibility in Planner

A Planner tab is a parameter configuration. A replicate is one configuration with one saved seed. A retry or replay creates another **attempt of that replicate**, never another independent observation.

## Using Planner

The GUI opens with an empty project. Use **Import Project** to open your workflow, and **Save Project** or **Export Project** to keep edits before closing or reloading the page. Saved project files include Planner configurations and replication settings.

1. Set **Replicates per configuration**. Existing workflows start at one; the user chooses the required count.
2. Choose a saved master seed, an explicit comma-separated list of positive integer seeds, or fresh randomness. Fresh randomness is resolved and saved before execution. Seeds remain strings in the browser to preserve integers larger than JavaScript's exact number range.
3. Choose **Shared seeds** for paired comparisons or **Independent seed sets**. Set a different replicate count for an individual configuration if needed; clear that field to use the default.
4. Open **Results** and press **Run**. The enabled configurations run with their chosen replicate counts. Seeds and settings are saved automatically.
5. View plots and the execution log in **Results**. The console's **Stop** button stops execution and preserves completed work. Browser reloads and tab closure do not stop execution.

Planner contains planning controls only. It has no batch history, outcome statistics, reference selector, or provenance panel. Saved batches can still be continued, extended or replayed through the CLI below.

Renaming, reordering or removing tabs preserves history. Identical effective configuration/seed requests are deduplicated within a batch. The five p53 sensitivity files have 15 tabs but 12 distinct configurations: ten shared seeds produce 120 unique runs, rather than 150 independent observations. Cross-file deduplication requires preparing those files together with `--suite`.

## What is saved

Results use the workflow name and local date/time, followed by the configuration name and replicate number. For example:

```text
runs/glucose_boundary_2026-09-06_15-30-00/
  glc_bnd_5.0/
    replicate-001/
      attempt-001/   # original outputs
      attempt-002/   # retry or replay; original outputs remain intact
    replicate-002/
      attempt-001/   # another independent replicate
```

A second batch gets another top-level directory even with identical names and seeds. If names collide, a simple `_2`, `_3`, … suffix keeps folders separate. All plots, reporter CSVs, logs and executed workflows use the attempt directory. The Results tab shows workflow and configuration names with replicate numbers. Older folders remain in place and can still be read.

Each `runs/<batch-id>/` contains:

- `manifest.json` and append-only `plan-001.json`, `plan-002.json`, … revisions;
- effective workflows in `configurations/`, plus content-addressed file inputs in `inputs/`;
- `source.tar.gz`, containing engine/adapter Python sources and plugin manifests, and `working-tree.patch`;
- Git revision, source fingerprint, Python/package versions, thread settings and RNG scheme;
- `<configuration-name>/replicate-001/attempt-001/`, with the executed workflow, seed, status, log, numerical diagnostics, original time series and plots.

The run ID identifies a configuration/seed combination under the batch's code and environment. Preserve **batch ID and run ID together** when joining results. Separate batches with the same configuration, seed and provenance are also replays, not independent evidence.

Copy the whole experiment directory when archiving or sharing it. Snapshot input paths are rebased when the directory moves. Keep inputs inside the project before preparing. The freezer recognizes existing file/path-valued parameters (including CSV and BND inputs); plugins that construct filenames internally or obtain external data need their own explicit input provenance. Output filenames are not inputs. Restore the archived source into a separate project checkout and recreate the recorded environment before replaying on another machine; merely copying a manifest is insufficient.

Workers reject changed source, changed frozen inputs/configuration, and mismatched recorded Python/package/thread settings. Source changes during execution invalidate that attempt. Do not edit model code during a batch. Canvas edits only affect future batches. The Python source archive is authoritative for uncommitted source, including new files; a Git commit alone is not the complete model snapshot.

## Randomness and numerical limits

`occ-seed-v1` derives 128-bit seeds from the saved master seed, pairing group and replicate index using SHA-256. Independent mode also includes the persistent tab ID. Names, order, worker count, attempt number and SLURM index do not enter the seed derivation. Legacy top-level seed zero means fresh entropy; resolved seeds are always recorded and positive.

The executor seeds `env.rng`, Python `random`, and legacy NumPy global randomness once before initialization. MicroC gene initialization and single-gene selection now use `env.rng`. Process isolation prevents global generators from leaking between replicates. RNG states are not reset at each iteration.

Same-seed replay was checked for a short MicroC sensitivity workflow, including both full CSV trajectories and all endpoint metrics. Equal seeds across configurations support pairing but do not keep every biological event synchronized: birth, death and conditional random draws can change subsequent histories. Numeric reproducibility across CPUs, solvers and platforms still requires validation with an appropriate tolerance. Unseeded external/native random generators in other plugins are outside this verified MicroC path.

The coupled diffusion solver records non-convergence without changing its biological equations, iteration limits or tolerance. Runs with reported coupling failures are retained and excluded from valid endpoint estimates. A completed status is not a proof that every possible numerical issue has been detected.

## CLI summaries

The CLI can summarize existing reporter CSVs under `<subworkflow>/timeseries/`, using numeric values from their **final recorded row**. This does not assume that every reporter writes exactly at the simulation's last step. Different endpoint coordinates are not pooled or paired. For the sensitivity reporter, `gene_steps` takes precedence over iteration when present.

Summaries include valid/planned count, available metric n, raw replicate values, mean, SD, and a 95% Student t confidence interval for the mean. A single replicate has no estimable interval. Intervals describe Monte Carlo uncertainty, not biological calibration uncertainty. Failed runs remain recorded, and complete-case estimates should be interpreted alongside failure rates.

Replays retain all attempts and contribute at most one observation. Endpoint differences from a previous valid same-seed attempt are flagged as a replay mismatch; the earlier valid observation is retained. Missing metrics do not become zeros. Extinction remains a biological outcome when the workflow completes and its reporter records it.

The sensitivity collector reads nested batches, selects valid completed attempts, and includes batch/run/seed identity. Shared baselines appear on each requested sensitivity axis with the same run identity. They must not be counted again when combining axes. Legacy folders without verified completion/numerical status are excluded from the collector's analytical CSV; their plots remain viewable in Results.

## CLI and SLURM

The GUI, standard workflow CLI and scheduler workers use the same compiler and runner:

```bash
# Prepare without launching. Repeat --workflow to combine selected files.
.venv/bin/python opencellcomms_engine/tools/run_planner_batch.py \
  --suite opencellcomms_adapters/MicroC/workflows/sensitivity_analysis \
  --replicates 10 --master-seed 20260906 --prepare

# Use the actual path printed by preparation.
.venv/bin/python opencellcomms_engine/tools/run_planner_batch.py \
  --manifest runs/<batch-id>/manifest.json --action continue

# Retry one replicate with its original seed, retaining previous attempts.
.venv/bin/python opencellcomms_engine/tools/run_planner_batch.py \
  --manifest runs/<batch-id>/manifest.json --action replay --run-id <run-id>

# Add five replicates per requested configuration, then run remaining work.
.venv/bin/python opencellcomms_engine/tools/run_planner_batch.py \
  --manifest runs/<batch-id>/manifest.json --add-replicates 5

# Machine-readable progress or statistical summary.
.venv/bin/python opencellcomms_engine/tools/run_planner_batch.py \
  --manifest runs/<batch-id>/manifest.json --status
```

For SLURM, set up the environment once on the cluster with `bash run_microc_slurm.sh --install-only`. Then, from the repository root, submit the full sensitivity suite using one file:

```bash
sbatch run_sensitivity_slurm.sh
```

This prepares one saved plan and runs all enabled configurations and their replicates **sequentially in one job**. It reads all five `p53_sa_*.json` files and uses the replicate counts and seeds saved in them. To choose another default count or master seed, append `--replicates <count>` or `--master-seed <seed>` with your chosen positive integers. Per-configuration count overrides still apply. The four identical baselines share runs when their seeds match: the default suite has 15 requested configurations but 12 distinct ones.

Results use the readable, separate configuration/replicate/attempt folders described above. SLURM writes `microc_p53_sa_<jobid>.out` and `.err` in the submission directory, so no log directory needs preparing. These filename patterns follow the [SLURM sbatch reference](https://slurm.schedmd.com/sbatch.html#SECTION_FILENAME-PATTERN). The script uses the allocated CPU count for BLAS threads. Request enough wall time for the sequential suite using your cluster's normal `sbatch --time=...` option.

To continue an interrupted job, pass its saved manifest instead of starting a new suite: `sbatch run_sensitivity_slurm.sh runs/<batch-folder>/manifest.json`. Completed valid replicates are skipped; unfinished ones restart with their saved seeds in new attempt folders. Keep the model and environment unchanged.

Parallel arrays remain optional: prepare with `bash run_sensitivity_slurm.sh --prepare` (plus any chosen replicate/seed options), then submit the **printed array range and manifest path** with `sbatch --array=... run_sensitivity_slurm.sh runs/<batch-folder>/manifest.json`. Do not add `--array` to a fresh suite launch: each worker must use the same saved plan. Preparation uses `MICROC_THREADS` (eight by default); request the same CPU count for workers. No jobs are submitted automatically by either launcher.

Each array index selects a saved run, and duplicate worker claims are rejected. After an interrupted local worker, Continue can recover its stale claim. If a remote scheduler worker is killed abruptly, confirm it has ended on the cluster before manually removing its `.claim` file; a remote PID cannot safely be declared dead from another host. A killed plan update can similarly leave a `.plan-lock` requiring inspection. Never clear active claims.

Continue/retry restarts a replicate from the beginning. Resuming a checkpoint midway is not implemented; that needs the full simulation state and all generator states, beyond a saved seed.

## Verification commands

Run `npm run test:planner --prefix opencellcomms_gui` to verify empty startup and project import/export. Engine tests are in `opencellcomms_engine/tests/workflow/test_replication.py` and `test_planner_api.py`. The slow MicroC replay test also checks that every original output file remains byte-identical after replaying and adding another replicate.

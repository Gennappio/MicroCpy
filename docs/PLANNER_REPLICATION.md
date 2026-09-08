# Replication and reproducibility in Planner

A Planner tab is one parameter configuration. A replicate runs that
configuration with a different saved seed. A retry repeats the same replicate
and seed in a new attempt folder, so it is not another independent observation.

## The workflow stores the complete plan

Planner is for defining the experiment. Its tabs, replicate counts and seed
settings are stored together in the workflow JSON under
`metadata.gui.planner`. The workflow is the only editable plan.

Use **Import Project** to open a workflow. Set the configurations and
replication settings in Planner, then use **Save Project** or **Export Project**
to write them back to the workflow JSON. That saved workflow is the source used
by local and SLURM runs.

The replication block records:

- the default number of replicates per enabled configuration;
- generated seeds and their master seed, or an explicit seed list;
- whether configurations use shared or independent seed sets;
- any replicate-count override on an individual configuration.

Use shared seeds when comparing configurations as paired stochastic runs. Use
independent seeds when pairing has no scientific meaning. Replaying the same
configuration and seed checks reproducibility, but does not increase the
replicate count.

## Sensitivity-suite plan

Each of the five `p53_sa_*.json` workflows explicitly stores the same settings:

- 10 replicates per configuration;
- generated seeds with master seed `42`;
- shared pairing.

The suite contains 15 Planner configurations, 12 of them enabled. Four
baseline tabs have the same effective configuration, and shared pairing gives
them the same seeds, so the same ten simulations would be repeated if every
one ran. Only the glucose-boundary file's baseline tab is enabled; the other
three are present but disabled. The suite therefore executes 120 runs whether
the files are submitted together or as separate jobs, and the baseline is
counted only once when axes are combined.

Submit the complete sensitivity analysis from the repository root with one
command:

```bash
sbatch run_sensitivity_slurm.sh path/to/p53_sa_oxygen_consumption.json   # one file per job
sbatch run_sensitivity_slurm.sh                                           # the whole suite in one job
```

The launcher reads the stored Planner definition of the given workflow JSON
file (or of all five suite files) and runs it sequentially in one job; submit
one job per file to run the files concurrently. It has no command-line
replicate or seed overrides.
To change the experiment, change the Planner settings in the workflows and save
or export them before submission.

Set up the cluster environment once, if needed, with:

```bash
bash run_microc_slurm.sh --install-only
```

## Result folders

Each new execution gets readable, separate folders for configuration and
replicate. For example:

```text
runs/glucose_boundary_2026-09-06_15-30-00/
  glc_bnd_5.0/
    replicate-001/
      workflow.json
      run.log
      status.json
      ... normal simulation outputs ...
    replicate-002/
      workflow.json
      ...
```

A retry creates a sibling such as `replicate-001_retry-002` and leaves the
first result intact. This extra folder appears only when a retry is actually
run. A name collision gets a simple `_2`, `_3`, … suffix. Each replicate
folder contains the executed workflow copy and the normal logs, CSVs and plots.

The runner keeps frozen inputs, a source-code archive and a small execution
record in the hidden `.opencellcomms` folder. They support reproducibility,
safe execution and retries; they are not another plan. The editable plan
remains entirely in the workflow JSON. New runs do not create `manifest.json`,
`source.tar.gz` or `working-tree.patch` at the experiment root. The source
archive is saved as `.opencellcomms/source.tar.gz`; a separate patch is not
needed because the archive contains the relevant source files directly.

## Seed coverage in MicroC

`occ-seed-v1` derives a positive 128-bit seed from the saved master seed,
pairing group and replicate index using SHA-256. Independent pairing also uses
the persistent Planner-tab ID. Tab names, order, worker count and attempt
number do not alter the derived seed.

Before initialization, the executor seeds `env.rng`, Python `random` and the
legacy NumPy global generator. MicroC gene initialization and single-gene
selection use `env.rng`. The random streams continue throughout the run and are
not reset at each iteration.

A short MicroC replay has been checked for equal CSV trajectories and endpoint
metrics when the workflow and seed are unchanged. Equal seeds across different
configurations support paired analysis, but changing a condition can change the
number and order of later random draws. Reproducibility across CPUs, solvers or
platforms should still be checked with a scientifically suitable numerical
tolerance.

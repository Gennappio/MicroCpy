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

The suite contains 15 requested Planner configurations. Four baseline tabs have
the same effective configuration, and shared pairing gives them the same seeds.
That baseline is therefore reused, giving 120 distinct executions rather than
150 (15 configurations × 10 replicates). A shared baseline must be counted only
once when axes are combined.

Submit the complete sensitivity analysis from the repository root with one
command:

```bash
sbatch run_sensitivity_slurm.sh
```

The launcher reads the five workflow JSON files and runs their stored Planner
definitions sequentially in one job. It has no command-line replicate or seed overrides.
To change the experiment, change the Planner settings in the workflows and save
or export them before submission.

Set up the cluster environment once, if needed, with:

```bash
bash run_microc_slurm.sh --install-only
```

## Result folders

Each new execution gets readable, separate folders for configuration,
replicate and attempt. For example:

```text
runs/glucose_boundary_2026-09-06_15-30-00/
  glc_bnd_5.0/
    replicate-001/
      attempt-001/
        workflow.json
        run.log
        status.json
        ... normal simulation outputs ...
    replicate-002/
      attempt-001/
        workflow.json
        ...
```

A retry creates `attempt-002` and leaves the first attempt intact. A name
collision gets a simple `_2`, `_3`, … suffix. The attempt folder contains the
executed workflow copy and the normal logs, CSVs and plots.

The runner also writes an immutable execution record inside the results for
provenance, retry safety and duplicate detection. It is generated
automatically from the workflows and is output only: users never provide, edit
or import it as a plan. It is not a second editable plan.

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

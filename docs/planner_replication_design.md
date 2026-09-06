# Planner replication and reproducibility — proposed design

Historical proposal, superseded by the simpler interface described in [current usage](PLANNER_REPLICATION.md). The results/provenance panel, reference selector and pilot preset were removed at the user's request. Planner contains configuration and replication settings; Results owns execution and plots. Output folders use readable names. The remaining sections preserve the original design discussion, not the current UI specification.

## Scientific behavior

Replication estimates variation across independent stochastic runs. Reproducibility makes a particular stochastic run replayable. Repeating one seed on an unchanged configuration is a replay, not another independent observation.

The user chooses the replicate count; no pilot count is prescribed by the interface. Cells and successive time points within a run are not independent replicates.

Default sensitivity studies to a shared seed list across comparable configurations. Replicate r of each configuration uses the same seed, allowing analysis of paired outcome differences. Different replicate indices receive different streams. A matching seed does not guarantee perfectly synchronized cell histories: births, deaths, and conditional draws can diverge. Common random numbers can reduce uncertainty in contrasts when they induce positive covariance; this benefit must be assessed rather than assumed.

Offer independently generated seed lists across configurations for users who need independent treatment samples. Pairing groups may span multiple workflow files, so the five sensitivity workflows can share one exported seed plan. Use explicit seed-list import to share a design across files without dependence on filenames or GUI order.

The current suite contains 15 tabs but 12 distinct parameter configurations: four tabs repeat the same baseline. With 10 shared seeds that is 150 requested executions but only 120 distinct configuration/seed pairs. Show those duplicate requests. Reuse a verified shared baseline or retain duplicate attempts as replays; never count identical configuration/seed pairs as independent observations.

## Planner controls

Keep existing parameter canvases and sparse overrides. Add a compact Run settings strip above the tabs:

- Replicates per configuration: integer, default 1 for backward compatibility. The example sensitivity plan uses 10.
- Seed set: generated from a saved master seed, or an explicit imported seed list.
- Compare configurations: shared seeds (paired) or independent seeds.
- Seed preview: resolved seeds and replicate numbers; regenerate only through an explicit New seed set action.
- Total work: enabled configurations, requested runs, distinct configuration/seed pairs, and duplicate baseline requests where applicable.

Each tab shows its replicate count next to its name. The active tab can inherit the Planner count or override it. Under shared seeding, an override selects a prefix of the same seed list: increasing 10 to 20 adds replicates 11–20 while preserving the first ten. A disabled tab schedules nothing. Rename/reorder changes presentation only.

Mark a configuration as the comparison reference. This is analysis metadata, not a biological parameter and not another canvas node.

An expandable Run plan shows configuration, replicate, resolved seed, output identity, and status. During execution it shows real planned/running/completed/failed/cancelled status and separately numerical validity. Results summarize completed valid independent replicates; missing/failed replicates remain visible.

Provide these actions with distinct meanings:

- Run new batch: freeze the current configurations and seed plan in a new batch.
- Continue batch: run missing work from the same frozen plan.
- Retry failed: start the same replicate from the beginning with its original seed, preserving the failed attempt.
- Add replicates: append new independent seed identities; preserve all existing ones and the frozen model.
- Replay replicate: create another attempt with exactly the original model/input/seed snapshot.

Checkpoint continuation is a later feature. It requires all RNG states plus counters and the remaining simulation state; a seed alone is insufficient.

## Deterministic RNG ownership

The existing typed API already exposes [env.rng](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_engine/src/biology/context.py:540). Complete that contract before claiming reproducibility.

Audit all random draws in the active MicroC path, including gene initialization, single-gene updates, per-agent ordering, division/movement decisions, and daughter-cell initialization. Currently some use global Python random, others global NumPy random, while the executor seeds only a separate NumPy Generator.

Resolve the effective replicate seed before initialization. Route the active stochastic path through an owned run RNG; do not reseed inside node functions or iterations. For legacy functions that cannot be migrated immediately, seed their global generators at the beginning of each isolated process and explicitly track this compatibility path. Process isolation is required if such globals remain.

For the first implementation, favor the existing env.rng accessor. If stronger matching of initial states across configurations is required, introduce stable named streams for initialization, gene updates, ordering, and division, derived from the replicate seed. This prevents extra draws in one subsystem from shifting every other subsystem. Named streams still do not guarantee event-by-event coupling across changing cell populations.

Use deterministic stream derivation such as NumPy SeedSequence with replicate index, stable stream/group identity, and the master seed. Do not derive seeds from process ID, SLURM worker index, tab display name, tab position, or Python's randomized hash(). Store the resolved seed/stream specification in the plan. Check duplicate seeds within a configuration, and use a sufficiently large seed representation rather than silently narrowing it.

For shared seeds, derive from the pairing group and replicate identity; for independent seeds, also include the tab's persistent identity. Reordering, retrying, changing worker counts, or running jobs sequentially must not change a replicate's random stream. [NumPy's parallel RNG guidance](https://numpy.org/doc/stable/reference/random/parallel.html) describes SeedSequence and stable identity-based derivation.

Fresh randomness is an explicit mode that resolves to a concrete saved seed before initialization. The current special value zero means fresh entropy; the effective seed must no longer remain unrecorded.

Seeded randomness is necessary but not sufficient: keep model iteration order stable, prevent unordered containers or unpredictable IDs from affecting execution order, and record the environment. Promise exact numerical replay only within a validated execution environment; compare supported platforms with explicit tolerances. [NumPy's compatibility policy](https://numpy.org/doc/stable/reference/random/compatibility.html) explains the limits of random-stream compatibility.

## Saved design and immutable execution plan

Extend the existing Planner metadata, with a schema version and explicit defaults. Conceptually:

```json
{
  "version": 2,
  "replication": {
    "replicates": 10,
    "seedMode": "generated",
    "masterSeed": "20260906",
    "pairing": "shared",
    "pairingGroup": "p53-sensitivity"
  },
  "tabs": [{
    "id": "stable-tab-id",
    "name": "glc_cons_7.0",
    "enabled": true,
    "role": "reference",
    "replicationOverride": null,
    "parameterOverrides": {}
  }]
}
```

For explicit seed mode, the saved seed list owns its length; do not maintain an independent conflicting count. In generated mode, the master seed and indexed derivation own the list. Replicate overrides use a documented prefix/extension rule.

At launch, the backend compiles this design into one immutable manifest shared by GUI, CLI, and SLURM. It freezes effective parameter values, input paths/content hashes, seed plan, execution horizon, and result destinations. Editing the canvas afterward changes only the next batch.

Each run record includes batch ID, stable configuration identity, display name, configuration fingerprint, replicate index, pairing group, seed, attempt number, timestamps, completion status, numerical validity, and exit code.

Each run retains the executed workflow, relevant input files or immutable references plus their hashes, code revision and local modifications, dependency/solver versions, RNG scheme/version, and relevant runtime settings. A Git revision alone is insufficient if the working tree is dirty. Store enough to reconstruct the code snapshot; a hash only detects a mismatch.

Execution identity is based on effective model configuration, inputs, code/environment, seed scheme, and seed. Cosmetic tab names are excluded. Duplicate detection across workflows requires comparing normalized resolved configurations and inputs, not raw JSON filenames.

## Execution and result retention

Use a hierarchy such as:

```text
runs/<batch-id>/<configuration-id>/replicate-001/attempt-001/
```

Display readable configuration names through the manifest. A rename cannot change historical result ownership.

The [current API clears an existing run directory and prunes folders absent from keep_labels](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_gui/server/api.py:408). Replace this behavior for planned batches with immutable result retention. Removing a tab must not delete scientific evidence. Cleanup should be a separate explicit action.

Compile run expansion once in [engine Planner code](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_engine/src/workflow/planner.py). The GUI currently expands tabs itself in [WorkflowConsole](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_gui/src/components/WorkflowConsole.jsx:395), while the [CLI has a separate expansion loop](/Users/gennaroabbruzzese/Activities/BIDSA/OpenCellComms_main/MicroCpy/opencellcomms_engine/tools/run_sim.py:1309). Both should consume the same resolved run plan.

The GUI submits the batch and observes a persisted backend queue; do not keep the only queue in a browser loop that disappears on refresh. Start with serial local execution because the backend currently supports one simulation process. Parallel execution can use isolated workers later.

SLURM assigns one manifest run to each array task. Scheduler job indices identify work; they do not determine its seed. Generate array length from the frozen manifest, replacing the fixed 0–14 range. Resume/retry operates against that manifest, unaffected by later edits to workflow files.

The Results browser and sensitivity collector must discover run manifests and nested attempts rather than assuming one flat folder per tab. Retain a reader for legacy outputs, marking their provenance or seed as unavailable when appropriate.

## Analysis

Keep raw replicate trajectories. Aggregate within exact configuration and compatible execution horizon, excluding incomplete/numerically invalid runs from endpoint estimates while reporting their counts.

Show valid n / planned n, individual replicate values, mean or median, and an uncertainty interval. A confidence interval for the mean and the spread of individual runs are different quantities and must be labeled accordingly.

For shared seeds, compare each treatment replicate with the matching baseline replicate; estimate uncertainty from the independent paired differences. Shared baselines across multiple contrasts must not be counted as separate samples. For independent seeding, use independent-sample comparisons.

As replication grows, monitor uncertainty on the primary outcomes and on treatment differences. Set scientifically meaningful precision goals in advance. Extinction is a model outcome, not automatically an invalid run. Frequent solver failures under a parameter setting are themselves relevant and cannot be concealed by success-only summaries.

## Implementation order and acceptance criteria

1. RNG audit and owned seeding. Two fresh processes with the same fixed seed/configuration/input/environment reproduce numerical time series; different seeds change a genuinely stochastic fixture.
2. Shared run-plan compiler, immutable manifests, and retention. GUI/CLI/SLURM yield identical execution identities and seed assignments for the same saved design; retries preserve identities and history.
3. Planner controls, store, and import/export. Update PlannerView, plannerSlice, workflowIOSlice, and loading paths together; round-trip replication settings; preserve old files as one replicate; extending counts preserves earlier seeds.
4. Results/collector aggregation. Verify incomplete and invalid runs are visible, retries are not independent samples, and repeated baseline requests are detected.
5. Pilot campaign. Run the chosen initial replication count, inspect uncertainty and convergence, then extend using the same frozen model and additional seed identities.

This proposal changes experiment management and RNG ownership. It does not rescale propagation time or change the biological laws discussed earlier.

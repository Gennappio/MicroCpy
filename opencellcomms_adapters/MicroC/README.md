# MicroC Adapter

A standalone re-expression of the jayatilake v7 tumor-microenvironment model in the new ABM workflow format.

This adapter contains its own copies of all adapter-side Python functions (gene network propagation, cell fate marking, plotting) plus the data files. It runs independently of the jayatilake adapter.

## Structure (new ABM format)

- **Agent kind**: `tumor_cell`
  - Init: `setup_population` + `read_checkpoint` + `initialize_netlogo_gene_networks`
  - Behaviors:
    - `gene_update`: substance→input mapping + NetLogo gene network propagation
    - `fate_update`: necrotic / growth-arrest / apoptotic / proliferating marking
    - `division`: cell division + apoptotic removal
- **Environment**:
  - Init: `setup_simulation` + `setup_domain` + `setup_substances` + `setup_associations`
  - Behaviors:
    - `diffusion_step`: coupled multi-substance PDE solver
    - `iteration_plots`: per-step plot generation
- **Scheduler** (30 iterations):
  `diffusion_step → gene_update → fate_update → division → iteration_plots`
- **Processing**: `final_summary` (summary plots)

## Running

```bash
python opencellcomms_engine/run_workflow.py --workflow opencellcomms_adapters/MicroC/workflows/microc.json
```

Should reproduce the same per-step cell counts and final plots as the v7 jayatilake workflow.

## Per-behavior subworkflow files

Because MicroC behaviors reference functions across multiple `.py` files
(engine + adapter), the per-behavior `.subworkflow.json` files live under
`MicroC/behaviors/` rather than next to a single `.py` file. These are in the
same format the GUI produces with **Export Behavior**, and can be re-imported
individually via **Import Subworkflow** in the palette.

## Editing the workflow

Edit `workflows/microc.json` directly, or open it in the GUI and re-export via **Export Project**.

## Conflict note

Both jayatilake and MicroC adapters register functions with the same names. When both are imported, the second registration is a benign overwrite (same code). If the engine ever raises on duplicates, comment out the jayatilake import in `opencellcomms_engine/src/workflow/registry.py`.

"""Per-iteration CSV of the one-factor-at-a-time sensitivity metrics.

One row per scheduler iteration, written to plots_dir/timeseries/<csv_filename>
and rewritten in full each iteration, the convention of the sibling reporters
record_gene_fate_counts and record_metabolic_symbiosis.

COLUMNS
    iteration            scheduler loop counter (loop_iteration; env.step stays 0)
    gene_steps           iteration x propagation_steps: gene-network updates per
                         cell so far, the clock on which runs with different
                         propagation step counts are comparable
    propagation_steps    single-gene updates per scheduler step in effect
                         (provenance; blank, with gene_steps, if no updater
                         published it)
    N_total              every cell in the population
    N_viable             cells whose phenotype is neither Necrosis nor Apoptosis
    N_proliferating, N_quiescent, N_growth_arrest, N_apoptotic, N_necrotic
                         phenotype census. Quiescent and Growth_Arrest are two
                         distinct MicroC phenotypes and are counted separately.
    N_mitoATP, N_glycoATP
                         cells with the mitoATP / glycoATP gene ON
    R_MG                 N_mitoATP / N_glycoATP (blank when N_glycoATP is 0)
    N_atp_ok, F_ATP      viable cells passing the ATP gate, and their fraction
                         of N_viable
    atp_threshold1       the gate fraction in effect (provenance)
    F_proliferating, F_quiescent, F_growth_arrest, F_apoptotic, F_necrotic
                         phenotype fractions of N_total
    F_inactive           1 - F_proliferating (every cell that is not proliferating)
    N_oxygenated, N_hypoxic, F_hypoxic
                         oxygen-region census; F_hypoxic is a fraction of N_total
    hypoxia_threshold_mM the region threshold in effect (provenance)
    MSI_mct1, MSI_mito   metabolic symbiosis index, both readings (see below)
    glucose_min_mM, oxygen_min_mM
                         minimum of the whole solver field
    tumor_radius_um      distance from the domain centre to the farthest cell
    domain_size_um       size_x of the domain
    relative_tumor_size  tumor_radius_um / (domain_size_um / 2)

LAWS AND THEIR OWNERS (docs/READABILITY.md R2)
    ATP gate      atp_rate > atp_threshold1 x atp_rate_max, the shared predicate
                  atp_gate_passes() of Mark Proliferating Cells (ATP + cell
                  cycle gated). atp_threshold1 is read from
                  results['proliferation_gate'], which that node publishes every
                  step from its Proliferation Gate table; this node owns no copy.
                  Without that node the three ATP columns stay blank and one
                  log line says so.
    Oxygen region oxygenated iff Oxygen at the cell >= hypoxia_threshold, the
                  shared census oxygen_region_census() of Record Metabolic
                  Symbiosis. hypoxia_threshold is this node's own parameter
                  (default 0.022 mM, the Oxygen_supply association threshold).
    MSI           symbiosis_index() of Record Metabolic Symbiosis. MSI_mct1
                  counts MCT1-ON cells as lactate-metabolic, MSI_mito counts
                  mitoATP-ON cells; phi_G is glycoATP ON in both.
    Radius        cell.position is a biological-grid index; the physical
                  position is index x Cell Height (the shared law in
                  src/core/coords.py) and the centre is (size_x/2, size_y/2)
                  from config.domain (Setup Domain). The centre-relative seed
                  loader places index offset bio_grid//2 there.
    Field minima  the solver arrays of the Glucose and Oxygen substances over
                  the whole domain.
    Gene clock    propagation_steps is read from results['gene_propagation'],
                  published by the Propagate Gene Networks node from its
                  Propagation Steps parameter (gene_propagation_record).

WHY raw_context FOR THE ITERATION NUMBER
    As in the sibling reporters: MicroC's scheduler does not advance the engine
    clock, so the loop counter is context['loop_iteration'].
"""

import math
from typing import Any, Dict, List, Optional

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext, Phenotype

from opencellcomms_adapters.MicroC.functions.fate.mark_proliferating_cells_gated import (
    atp_gate_passes,
)
from opencellcomms_adapters.MicroC.functions.gene_network.gene_propagation_record import (
    published_propagation_steps,
)
from opencellcomms_adapters.MicroC.functions.reporting.record_metabolic_symbiosis import (
    oxygen_region_census,
    symbiosis_index,
    write_history_csv,
)

_DEAD_FATES = {Phenotype.NECROSIS.value, Phenotype.APOPTOSIS.value}
_PHENOTYPE_COLUMNS = (
    ("proliferating", Phenotype.PROLIFERATION.value),
    ("quiescent", Phenotype.QUIESCENT.value),
    ("growth_arrest", Phenotype.GROWTH_ARREST.value),
    ("apoptotic", Phenotype.APOPTOSIS.value),
    ("necrotic", Phenotype.NECROSIS.value),
)


@register_function(
    requires=['population', 'simulator'],
    display_name="Record Sensitivity Metrics",
    description=(
        "Per-iteration CSV of the sensitivity-analysis metrics: phenotype census and "
        "fractions (viable = not Necrosis/Apoptosis; F_inactive = 1 - F_proliferating), "
        "mitoATP/glycoATP counts and R_MG, fraction of viable cells passing the ATP gate "
        "atp_rate > atp_threshold1 x atp_rate_max (atp_threshold1 read from "
        "results['proliferation_gate'] as published by Mark Proliferating Cells (ATP + "
        "cell cycle gated)), oxygen-region census and MSI (the laws of Record Metabolic "
        "Symbiosis), whole-field Glucose and Oxygen minima, tumour radius = max distance "
        "of a cell (index x Cell Height) from the domain centre, and relative tumour "
        "size = radius / (domain size / 2)."
    ),
    category="FINALIZATION",
    parameters=[
        {"name": "hypoxia_threshold", "type": "FLOAT",
         "description": "Oxygen concentration (mM) separating hypoxic from oxygenated "
                        "cells for N_hypoxic / F_hypoxic and the MSI regions. Defaults "
                        "to 0.022, the Oxygen_supply association threshold, so a cell "
                        "is hypoxic exactly when its Oxygen_supply gene input is OFF.",
         "default": 0.022},
        {"name": "csv_filename", "type": "STRING",
         "description": "Output file, written under plots_dir/timeseries",
         "default": "sensitivity_metrics_over_time.csv"},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
    collective=True,
    compatible_kernels=["biophysics"],
    contract={
        "phase": "reporting",
        "owner": {"type": "agent", "kind": "tumor_cell"},
        "reads": ["agent.collection", "agent.self.gene_states", "resource.fields",
                  "simulation.results", "simulation.config"],
        "writes": [],
        "emits": [],
    },
)
def record_sensitivity_metrics(
    env: BiologicalContext,
    hypoxia_threshold: float = 0.022,
    csv_filename: str = "sensitivity_metrics_over_time.csv",
    **kwargs,
) -> bool:
    ctx = env.raw_context
    history: List[Dict[str, Any]] = ctx.setdefault("sensitivity_history", [])

    iteration = ctx.get("loop_iteration")
    try:
        iteration = int(iteration)
    except (TypeError, ValueError):
        iteration = len(history) + 1

    # One row per iteration whatever the calling convention: the executor runs
    # an all-collective subworkflow once, but a per-agent ask re-added by the
    # GUI would otherwise call this once per cell (see the sibling reporters).
    if history and history[-1]["iteration"] == iteration:
        return True

    dom = env.config.domain
    cell_height_um = dom.cell_height.micrometers
    size_x_um = dom.size_x.micrometers
    size_y_um = dom.size_y.micrometers
    centre = (size_x_um / 2.0, size_y_um / 2.0)

    gate = env.results.get('proliferation_gate')
    atp_threshold1: Optional[float] = None
    if isinstance(gate, dict) and gate.get('atp_threshold1') is not None:
        atp_threshold1 = float(gate['atp_threshold1'])
    propagation_steps = published_propagation_steps(env)

    _announce_sources(env, ctx, hypoxia_threshold, atp_threshold1, propagation_steps,
                      size_x_um, size_y_um, cell_height_um, csv_filename)

    # Oxygen regions, pathway counts and MSI: the shared census and law.
    census = oxygen_region_census(env, hypoxia_threshold)
    n_oxy, n_hypo = census.n_region['oxy'], census.n_region['hypo']
    msi: Dict[str, float] = {}
    for label in ("mct1", "mito"):
        msi[label] = symbiosis_index(
            l_oxy=census.counts[('oxy', label)], g_oxy=census.counts[('oxy', 'glyco')],
            l_hypo=census.counts[('hypo', label)], g_hypo=census.counts[('hypo', 'glyco')],
            n_oxy=n_oxy, n_hypo=n_hypo,
        )[0]

    # Phenotypes, the ATP gate over viable cells, and the tumour radius.
    phenotype_counts = {value: 0 for _, value in _PHENOTYPE_COLUMNS}
    n_total = n_viable = n_atp_ok = 0
    radius_um = 0.0
    for cell in env.cells:
        n_total += 1
        phenotype = cell.phenotype
        if phenotype in phenotype_counts:
            phenotype_counts[phenotype] += 1
        if phenotype not in _DEAD_FATES:
            n_viable += 1
            if atp_threshold1 is not None:
                _, atp_ok = atp_gate_passes(cell.metabolic_state, atp_threshold1)
                n_atp_ok += int(bool(atp_ok))
        pos = cell.position
        radius_um = max(radius_um, math.hypot(pos[0] * cell_height_um - centre[0],
                                              pos[1] * cell_height_um - centre[1]))

    glucose_min = _field_min(env, ctx, 'Glucose')
    oxygen_min = _field_min(env, ctx, 'Oxygen')

    def frac(numerator: int, denominator: int) -> Any:
        return round(numerator / denominator, 6) if denominator else ""

    n_prolif = phenotype_counts[Phenotype.PROLIFERATION.value]
    have_gate = atp_threshold1 is not None
    row: Dict[str, Any] = {
        "iteration": iteration,
        "gene_steps": iteration * propagation_steps if propagation_steps is not None else "",
        "propagation_steps": propagation_steps if propagation_steps is not None else "",
        "N_total": n_total,
        "N_viable": n_viable,
    }
    for column, value in _PHENOTYPE_COLUMNS:
        row[f"N_{column}"] = phenotype_counts[value]
    row.update({
        "N_mitoATP": census.n_mito,
        "N_glycoATP": census.n_glyco,
        "R_MG": round(census.n_mito / census.n_glyco, 6) if census.n_glyco else "",
        "N_atp_ok": n_atp_ok if have_gate else "",
        "F_ATP": frac(n_atp_ok, n_viable) if have_gate else "",
        "atp_threshold1": atp_threshold1 if have_gate else "",
    })
    for column, value in _PHENOTYPE_COLUMNS:
        row[f"F_{column}"] = frac(phenotype_counts[value], n_total)
    row.update({
        "F_inactive": round(1.0 - n_prolif / n_total, 6) if n_total else "",
        "N_oxygenated": n_oxy,
        "N_hypoxic": n_hypo,
        "F_hypoxic": frac(n_hypo, n_total),
        "hypoxia_threshold_mM": hypoxia_threshold,
        "MSI_mct1": round(msi['mct1'], 6),
        "MSI_mito": round(msi['mito'], 6),
        "glucose_min_mM": glucose_min,
        "oxygen_min_mM": oxygen_min,
        "tumor_radius_um": round(radius_um, 3),
        "domain_size_um": round(size_x_um, 6),
        "relative_tumor_size": round(radius_um / (size_x_um / 2.0), 6) if size_x_um else "",
    })

    history.append(row)

    output_dir = env.plots_dir / "timeseries"
    output_dir.mkdir(parents=True, exist_ok=True)
    write_history_csv(output_dir / csv_filename, history)

    print(
        f"[SENSITIVITY] Iteration {iteration} (gene_steps={row['gene_steps']}, n={n_total}): "
        f"viable={n_viable}, "
        f"prolif={n_prolif}, quiescent={row['N_quiescent']}, GA={row['N_growth_arrest']}, "
        f"apo={row['N_apoptotic']}, necro={row['N_necrotic']} | "
        f"mito={census.n_mito}, glyco={census.n_glyco}, R_MG={row['R_MG']} | "
        f"F_ATP={row['F_ATP']} | hypoxic={n_hypo} (F={row['F_hypoxic']}) | "
        f"MSI mct1={row['MSI_mct1']} mito={row['MSI_mito']} | "
        f"glc_min={glucose_min} O2_min={oxygen_min} | "
        f"r={row['tumor_radius_um']} um (rel={row['relative_tumor_size']})"
    )
    return True


def _field_min(env: BiologicalContext, ctx: Dict[str, Any], name: str) -> Any:
    """Minimum of a substance's whole solver field, or blank (logged once) if absent."""
    substances = env.environment.raw_simulator.state.substances
    state = substances.get(name)
    if state is None:
        missing = ctx.setdefault('_sensitivity_missing_fields', set())
        if name not in missing:
            missing.add(name)
            print(f"[SENSITIVITY] no '{name}' field in the solver: "
                  f"{name.lower()}_min_mM left blank")
        return ""
    return round(float(state.concentrations.min()), 9)


def _announce_sources(env: BiologicalContext, ctx: Dict[str, Any],
                      hypoxia_threshold: float, atp_threshold1: Optional[float],
                      propagation_steps: Optional[int],
                      size_x_um: float, size_y_um: float, cell_height_um: float,
                      csv_filename: str) -> None:
    """Once per run, name every value source this node reads (READABILITY R1.5)."""
    if ctx.get('_sensitivity_sources_announced'):
        return
    ctx['_sensitivity_sources_announced'] = True

    substances = getattr(env.config, 'substances', None) or {}

    def bounds(name: str) -> str:
        sub = substances.get(name)
        if sub is None:
            return f"{name}: not configured"
        b, i = sub.boundary_value, sub.initial_value
        return (f"{name} boundary={b.value:g} {b.unit} initial={i.value:g} {i.unit} "
                f"({sub.boundary_type})")

    if atp_threshold1 is not None:
        gate_txt = (f"atp_threshold1={atp_threshold1:g} from results['proliferation_gate'] "
                    f"(Mark Proliferating Cells (ATP + cell cycle gated))")
    else:
        gate_txt = ("results['proliferation_gate'] not published (Mark Proliferating "
                    "Cells (ATP + cell cycle gated) did not run before this node): "
                    "N_atp_ok, F_ATP, atp_threshold1 left blank")

    if propagation_steps is not None:
        clock_txt = (f"gene_steps = iteration x {propagation_steps} from "
                     f"results['gene_propagation'] (Propagate Gene Networks, Propagation Steps)")
    else:
        clock_txt = ("results['gene_propagation'] not published (no Propagate Gene "
                     "Networks node ran before this node): gene_steps, propagation_steps left blank")

    print(
        "[SENSITIVITY] sources in effect: "
        f"hypoxia_threshold={hypoxia_threshold:g} mM (this node's Hypoxia Threshold "
        f"parameter); ATP gate {gate_txt}; {clock_txt}; domain {size_x_um:g}x{size_y_um:g} um, "
        f"cell_height {cell_height_um:g} um (Setup Domain via config.domain); "
        f"{bounds('Glucose')}; {bounds('Oxygen')} (Substance (JSON) nodes via "
        "config.substances); viable = phenotype not in {Necrosis, Apoptosis}; "
        "tumor_radius = max |cell index x cell_height - domain centre|; "
        f"CSV -> {env.plots_dir / 'timeseries' / csv_filename}"
    )
    if size_x_um != size_y_um:
        print(f"[SENSITIVITY] WARNING: domain is not square ({size_x_um:g}x{size_y_um:g} um); "
              "relative_tumor_size divides by size_x / 2")

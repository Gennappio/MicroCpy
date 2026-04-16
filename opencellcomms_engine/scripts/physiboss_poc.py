#!/usr/bin/env python3
"""
PhysiBoss Proof-of-Concept — Phase 0.5

Standalone script that:
1. Parses a PhysiCell XML config
2. Creates a CellContainer with cells
3. Applies the coupling: fixed TNF concentration → BN thresholds → fate rates
4. Runs 10 phenotype steps (no MaBoSS — uses thresholded mock)
5. Prints per-step fate statistics

Usage:
    python scripts/physiboss_poc.py [path/to/XML]

If no XML is given, uses built-in defaults matching the TNF tutorial.
"""

import sys
import os
import numpy as np

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.biology.cell_container import CellContainer, phenotype_id, phenotype_name
from src.adapters.physiboss.coupling import PhysiBossSubstrateCoupling
from src.adapters.physiboss.phenotype_mapper import PhysiBossPhenotypeMapper
from src.adapters.physiboss.config_loader import (
    PhysiBossConfigLoader, InputMapping, OutputMapping,
)


def main():
    xml_path = sys.argv[1] if len(sys.argv) > 1 else None

    # ── 1. Load or build config ─────────────────────────────────────────
    if xml_path and os.path.exists(xml_path):
        print(f"Loading XML config: {xml_path}")
        loader = PhysiBossConfigLoader(xml_path)
        config = loader.load()
        print(f"  Domain: {config.domain.x_min}..{config.domain.x_max}")
        print(f"  Substrates: {[s.name for s in config.substrates]}")
        print(f"  Cell types: {[cd.name for cd in config.cell_definitions]}")
    else:
        config = None
        print("No XML provided — using built-in TNF tutorial defaults")

    # ── 2. Set up coupling ──────────────────────────────────────────────
    if config and config.coupling:
        coupling = PhysiBossSubstrateCoupling.from_config(config.coupling)
        dt_pheno = config.timing.dt_phenotype
        print(f"  Coupling inputs:  {[i.node_name for i in coupling.inputs]}")
        print(f"  Coupling outputs: {[o.node_name for o in coupling.outputs]}")
    else:
        # Built-in defaults matching 1_Long_TNF.xml
        coupling = PhysiBossSubstrateCoupling(
            inputs=[
                InputMapping(
                    substance_name="TNF", node_name="TNF",
                    threshold=1.0, action="activation",
                ),
            ],
            outputs=[
                OutputMapping(
                    node_name="Apoptosis", behaviour_name="apoptosis",
                    value=1e6, base_value=0.0, action="activation",
                ),
                OutputMapping(
                    node_name="NonACD", behaviour_name="necrosis",
                    value=1e6, base_value=0.0, action="activation",
                ),
            ],
        )
        dt_pheno = 6.0

    mapper = PhysiBossPhenotypeMapper(dt_phenotype=dt_pheno)

    # ── 3. Create CellContainer ─────────────────────────────────────────
    N_CELLS = 500
    container = CellContainer(capacity=N_CELLS * 2, dimensions=2)

    # Place cells in a disc of radius 250 µm
    rng = np.random.default_rng(42)
    angles = rng.uniform(0, 2 * np.pi, N_CELLS)
    radii = 250.0 * np.sqrt(rng.uniform(0, 1, N_CELLS))
    positions = np.column_stack([radii * np.cos(angles), radii * np.sin(angles)])
    container.add_cells(positions, phenotype="Quiescent")

    # Register BN output columns
    container.add_float_column("bn_prob_Apoptosis", default=0.0)
    container.add_float_column("bn_prob_NonACD", default=0.0)

    print(f"\n  Created {container.n} cells in disc (r=250 µm)")
    print(f"  Initial phenotypes: {container.phenotype_counts()}")

    # ── 4. Simulate: TNF concentration = 10.0 everywhere ────────────────
    TNF_CONC = 10.0
    N_STEPS = 10

    print(f"\n  Running {N_STEPS} phenotype steps (TNF={TNF_CONC}, dt={dt_pheno} min)")
    print(f"  {'Step':>4}  {'Quiescent':>10}  {'apoptotic':>10}  {'necrotic':>10}  {'other':>8}")
    print("  " + "-" * 50)

    for step in range(N_STEPS):
        N = container.count

        # 4a. Vectorized coupling: TNF concentration → BN inputs
        tnf_array = np.full(N, TNF_CONC)
        bn_inputs = coupling.compute_bn_inputs_vectorized({"TNF": tnf_array})

        # 4b. Mock MaBoSS: if TNF node is ON, Apoptosis=0.7, NonACD=0.3
        #     (In real use, pyMaBoSS would compute these probabilities)
        tnf_on = bn_inputs.get("TNF", np.zeros(N, dtype=np.bool_))
        container.get_float("bn_prob_Apoptosis")[:N] = np.where(tnf_on, 0.7, 0.0)
        container.get_float("bn_prob_NonACD")[:N] = np.where(tnf_on, 0.3, 0.0)

        # 4c. Vectorized coupling: BN probs → rates
        bn_probs = {
            "Apoptosis": container.get_float("bn_prob_Apoptosis")[:N],
            "NonACD": container.get_float("bn_prob_NonACD")[:N],
        }
        cell_rates = coupling.apply_phenotype_outputs_vectorized(bn_probs, N)

        # 4d. Vectorized phenotype decisions
        old_phenos = container.phenotype_ids[:N].copy()
        new_phenos = mapper.apply_rates_vectorized(cell_rates, old_phenos, dt_pheno)
        container.phenotype_ids[:N] = new_phenos

        # Print stats
        counts = container.phenotype_counts()
        q = counts.get("Quiescent", 0)
        a = counts.get("apoptotic", 0)
        n = counts.get("necrotic", 0)
        other = sum(v for k, v in counts.items() if k not in ("Quiescent", "apoptotic", "necrotic"))
        print(f"  {step + 1:>4}  {q:>10}  {a:>10}  {n:>10}  {other:>8}")

    # ── 5. Final summary ────────────────────────────────────────────────
    print(f"\n  Final phenotype distribution:")
    for name, count in sorted(container.phenotype_counts().items()):
        pct = 100.0 * count / container.n if container.n > 0 else 0
        print(f"    {name:>15}: {count:>5} ({pct:5.1f}%)")

    print(f"\n  Total alive: {container.n} / {container.count}")
    print("  Done.")


if __name__ == "__main__":
    main()

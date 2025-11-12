"""
Standard workflow functions for MicroC.

These are high-level orchestrator functions that can be used in workflows.
They receive the full simulation context and can call helper functions.
"""

from typing import Dict, Any, Optional


def standard_intracellular_update(
    population,
    simulator,
    gene_network,
    config,
    dt: float,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Standard intracellular update workflow function.
    
    This is the default behavior when no custom workflow is specified.
    Calls all the standard intracellular operations in order:
    1. Update intracellular processes (metabolism, gene networks)
    2. Update gene networks based on environment
    3. Update phenotypes based on gene states
    4. Remove dead cells
    
    Args:
        population: Population object
        simulator: Diffusion simulator
        gene_network: Gene network object
        config: Configuration object
        dt: Time step
        helpers: Dictionary of helper functions
    """
    # Run intracellular processes (calls custom metabolism functions)
    helpers['update_intracellular']()
    
    # Update gene networks based on current environment
    helpers['update_gene_networks']()
    
    # Update phenotypes based on gene states
    helpers['update_phenotypes']()
    
    # Remove dead cells
    helpers['remove_dead_cells']()


def standard_diffusion_update(
    population,
    simulator,
    gene_network,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Standard diffusion update workflow function.
    
    This is the default behavior when no custom workflow is specified.
    Runs the diffusion solver with substance reactions from cells.
    
    Args:
        population: Population object
        simulator: Diffusion simulator
        gene_network: Gene network object
        config: Configuration object
        helpers: Dictionary of helper functions
    """
    # Run diffusion solver
    helpers['run_diffusion']()


def standard_intercellular_update(
    population,
    simulator,
    gene_network,
    config,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Standard intercellular update workflow function.
    
    This is the default behavior when no custom workflow is specified.
    Handles cell division, migration, and other intercellular processes.
    
    Args:
        population: Population object
        simulator: Diffusion simulator
        gene_network: Gene network object
        config: Configuration object
        helpers: Dictionary of helper functions
    """
    # Run intercellular processes (calls custom division/migration functions)
    helpers['update_intercellular']()


def custom_intracellular_with_logging(
    population,
    simulator,
    gene_network,
    config,
    dt: float,
    step: int,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Example custom intracellular function with logging.
    
    Shows how to add custom behavior around standard operations.
    """
    print(f"[CUSTOM] Starting intracellular update at step {step}")
    
    # Get cell count before
    cell_count_before = len(population.cells)
    
    # Run standard intracellular update
    helpers['update_intracellular']()
    helpers['update_gene_networks']()
    helpers['update_phenotypes']()
    helpers['remove_dead_cells']()
    
    # Get cell count after
    cell_count_after = len(population.cells)
    
    if cell_count_after < cell_count_before:
        print(f"[CUSTOM] {cell_count_before - cell_count_after} cells died")


def custom_diffusion_with_validation(
    population,
    simulator,
    gene_network,
    config,
    step: int,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Example custom diffusion function with validation.
    
    Shows how to add validation around diffusion.
    """
    # Get concentrations before
    conc_before = simulator.get_substance_concentrations()
    
    # Run diffusion
    helpers['run_diffusion']()
    
    # Get concentrations after
    conc_after = simulator.get_substance_concentrations()
    
    # Validate (example: check for negative concentrations)
    for substance_name, conc_field in conc_after.items():
        min_conc = conc_field.min()
        if min_conc < 0:
            print(f"[WARNING] Negative concentration detected for {substance_name}: {min_conc}")


def minimal_intracellular(
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Minimal intracellular update - only metabolism, no phenotype changes.
    
    Example of a custom workflow that skips certain operations.
    """
    # Only run metabolism, skip phenotype updates
    helpers['update_intracellular']()
    helpers['update_gene_networks']()
    # Deliberately skip: helpers['update_phenotypes']()
    helpers['remove_dead_cells']()


def no_death_intracellular(
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Intracellular update without cell death.
    
    Example of a custom workflow that prevents cell death.
    """
    helpers['update_intracellular']()
    helpers['update_gene_networks']()
    helpers['update_phenotypes']()
    # Deliberately skip: helpers['remove_dead_cells']()


def intracellular_with_analysis(
    population,
    simulator,
    step: int,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Intracellular update with real-time analysis.
    
    Example showing how to add custom analysis during simulation.
    """
    # Run standard updates
    helpers['update_intracellular']()
    helpers['update_gene_networks']()
    helpers['update_phenotypes']()
    helpers['remove_dead_cells']()
    
    # Custom analysis
    if step % 10 == 0:  # Every 10 steps
        phenotype_counts = {}
        for cell in population.cells.values():
            phenotype = cell.phenotype
            phenotype_counts[phenotype] = phenotype_counts.get(phenotype, 0) + 1
        
        print(f"[ANALYSIS] Step {step} phenotype distribution: {phenotype_counts}")


def diffusion_with_boundary_check(
    simulator,
    step: int,
    helpers: Dict[str, Any],
    **kwargs
) -> None:
    """
    Diffusion update with boundary condition checking.
    
    Example showing how to monitor boundary conditions.
    """
    # Run diffusion
    helpers['run_diffusion']()
    
    # Check boundary conditions
    if step % 50 == 0:  # Every 50 steps
        conc = simulator.get_substance_concentrations()
        for substance_name, conc_field in conc.items():
            mean_conc = conc_field.mean()
            print(f"[BOUNDARY] Step {step} - {substance_name} mean: {mean_conc:.6f}")


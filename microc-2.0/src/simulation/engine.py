"""
Simulation Engine - Orchestrates multi-timescale updates using SOLID-friendly design.
Keeps CLI, plotting, and file I/O out of the core loop.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from .orchestrator import TimescaleOrchestrator


@dataclass
class SimulationResults:
    """Container for simulation results (compatible with existing save/plot code)."""
    time: List[float]
    substance_stats: List[Dict[str, Dict[str, float]]]
    cell_counts: List[Dict[str, Any]]
    gene_network_states: List[Dict[str, bool]]

    @staticmethod
    def empty() -> "SimulationResults":
        return SimulationResults(time=[], substance_stats=[], cell_counts=[], gene_network_states=[])


class SimulationEngine:
    """
    Main engine coordinating population, diffusion, and gene-network updates.
    - No CLI concerns
    - No plotting/VTK I/O
    - Deterministic, testable orchestration
    """

    def __init__(self, config, simulator, population, gene_network, custom_functions: Optional[object] = None):
        self.config = config
        self.simulator = simulator
        self.population = population
        self.gene_network = gene_network
        self.custom_functions = custom_functions
        self.orchestrator = TimescaleOrchestrator(config.time, custom_functions)

    def run(self, num_steps: int, dt: Optional[float] = None, verbose: bool = False) -> SimulationResults:
        """
        Execute simulation for a fixed number of steps.
        Returns SimulationResults with time-series metrics.
        """
        dt = dt if dt is not None else self.config.time.dt
        results = SimulationResults.empty()

        for step in range(num_steps):
            current_time = step * dt

            # Decide which processes to update
            updates = self.orchestrator.step(step)

            # Intracellular processes (fast)
            if updates['intracellular']:
                self.population.update_intracellular_processes(dt)

            # Diffusion (medium)
            if updates['diffusion']:
                current_concentrations = self.simulator.get_substance_concentrations()
                substance_reactions = self.population.get_substance_reactions(current_concentrations)
                self.simulator.update(substance_reactions)

            # Gene networks react to latest environment
            if updates['diffusion'] or updates['intracellular']:
                substance_concentrations = self.simulator.get_substance_concentrations()
                self.population.update_gene_networks(substance_concentrations)
                self.population.update_phenotypes()
                self.population.remove_dead_cells()

            # Intercellular processes (slow)
            if updates['intercellular']:
                self.population.update_intercellular_processes()

            # Optionally adapt timing based on step time (kept minimal here)
            # Timing measurement and adaptation can be added via callbacks if needed

            # Collect data according to configured interval
            if step % self.config.output.save_data_interval == 0:
                results.time.append(current_time)
                results.substance_stats.append(self.simulator.get_summary_statistics())
                results.cell_counts.append(self.population.get_population_statistics())

                # Sample gene network state at center (backward compatible with existing tools)
                center_pos = (self.config.domain.nx // 2, self.config.domain.ny // 2)
                gene_inputs = self.simulator.get_gene_network_inputs_for_position(center_pos)
                self.gene_network.set_input_states(gene_inputs)
                gene_outputs = self.gene_network.step(1)
                results.gene_network_states.append(gene_outputs)

            if verbose and (step + 1) % max(1, num_steps // 10) == 0:
                # Lightweight progress
                print(f"[ENGINE] Step {step + 1}/{num_steps} ({(step + 1) / num_steps * 100:.1f}%)")

        return results


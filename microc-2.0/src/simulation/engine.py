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

    def __init__(self, config, simulator, population, gene_network, custom_functions: Optional[object] = None, workflow=None):
        self.config = config
        self.simulator = simulator
        self.population = population
        self.gene_network = gene_network
        self.custom_functions = custom_functions
        self.orchestrator = TimescaleOrchestrator(config.time, custom_functions)
        self.workflow = workflow
        self.workflow_executor = None

        # Initialize workflow executor if workflow is provided
        if workflow is not None:
            try:
                from ..workflow.executor import WorkflowExecutor
                self.workflow_executor = WorkflowExecutor(workflow, custom_functions, config)
                print(f"[WORKFLOW] Initialized workflow executor for: {workflow.name}")
            except Exception as e:
                print(f"[WORKFLOW] Failed to initialize workflow executor: {e}")
                self.workflow_executor = None

    def run(self, num_steps: int, dt: Optional[float] = None, verbose: bool = False) -> SimulationResults:
        """
        Execute simulation for a fixed number of steps.
        Returns SimulationResults with time-series metrics.

        If a workflow is provided, uses workflow-driven execution.
        Otherwise, uses default hardcoded behavior.
        """
        if self.workflow_executor is not None:
            return self._run_with_workflow(num_steps, dt, verbose)
        else:
            return self._run_default(num_steps, dt, verbose)

    def _run_default(self, num_steps: int, dt: Optional[float] = None, verbose: bool = False) -> SimulationResults:
        """
        Default hardcoded execution (no workflow).
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

                # Update gene networks and phenotypes after intracellular changes
                substance_concentrations = self.simulator.get_substance_concentrations()
                self.population.update_gene_networks(substance_concentrations)
                self.population.update_phenotypes()
                self.population.remove_dead_cells()

            # Diffusion (medium)
            if updates['diffusion']:
                current_concentrations = self.simulator.get_substance_concentrations()
                substance_reactions = self.population.get_substance_reactions(current_concentrations)
                self.simulator.update(substance_reactions)

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

            # Export cell states and substance fields (CSV for 2D, VTK for 3D)
            should_save_cellstate = (self.config.output.save_cellstate_interval > 0 and
                                    step % self.config.output.save_cellstate_interval == 0)
            if should_save_cellstate:
                self._export_cell_states(step)

            if verbose and (step + 1) % max(1, num_steps // 10) == 0:
                # Lightweight progress
                print(f"[ENGINE] Step {step + 1}/{num_steps} ({(step + 1) / num_steps * 100:.1f}%)")

        return results

    def _run_with_workflow(self, num_steps: int, dt: Optional[float] = None, verbose: bool = False) -> SimulationResults:
        """
        Workflow-driven execution.
        Uses workflow_executor to call custom functions at each stage.
        """
        dt = dt if dt is not None else self.config.time.dt
        results = SimulationResults.empty()

        print(f"[WORKFLOW] Running simulation with workflow: {self.workflow.name}")

        # Execute initialization stage once at the beginning
        if self.workflow.get_stage("initialization"):
            print(f"[WORKFLOW] Executing initialization stage...")
            context = self._build_context(step=0, dt=dt)
            self.workflow_executor.execute_initialization(context)

        for step in range(num_steps):
            current_time = step * dt

            # Decide which processes to update
            updates = self.orchestrator.step(step)

            # Build execution context for workflow functions
            context = self._build_context(step=step, dt=dt)

            # Intracellular stage (fast)
            if updates['intracellular']:
                # Execute workflow intracellular stage (if defined)
                # This allows custom pre/post processing around the standard intracellular update
                if self.workflow.get_stage("intracellular") and self.workflow.get_stage("intracellular").enabled:
                    self.workflow_executor.execute_intracellular(context)

                # Always run the standard intracellular update
                # This calls the custom functions registered in Population
                self.population.update_intracellular_processes(dt)

                # Update gene networks and phenotypes after intracellular changes
                substance_concentrations = self.simulator.get_substance_concentrations()
                self.population.update_gene_networks(substance_concentrations)
                self.population.update_phenotypes()
                self.population.remove_dead_cells()

            # Diffusion stage (medium)
            if updates['diffusion']:
                # Execute workflow diffusion stage (if defined)
                if self.workflow.get_stage("diffusion") and self.workflow.get_stage("diffusion").enabled:
                    self.workflow_executor.execute_diffusion(context)

                # Always run the diffusion solver
                current_concentrations = self.simulator.get_substance_concentrations()
                substance_reactions = self.population.get_substance_reactions(current_concentrations)
                self.simulator.update(substance_reactions)

            # Intercellular stage (slow)
            if updates['intercellular']:
                # Execute workflow intercellular stage (if defined)
                if self.workflow.get_stage("intercellular") and self.workflow.get_stage("intercellular").enabled:
                    self.workflow_executor.execute_intercellular(context)

                # Always run the standard intercellular update
                # This calls the custom functions registered in Population
                self.population.update_intercellular_processes()

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

            # Export cell states and substance fields (CSV for 2D, VTK for 3D)
            should_save_cellstate = (self.config.output.save_cellstate_interval > 0 and
                                    step % self.config.output.save_cellstate_interval == 0)
            if should_save_cellstate:
                self._export_cell_states(step)

            if verbose and (step + 1) % max(1, num_steps // 10) == 0:
                # Lightweight progress
                print(f"[ENGINE] Step {step + 1}/{num_steps} ({(step + 1) / num_steps * 100:.1f}%)")

        # Execute finalization stage once at the end
        if self.workflow.get_stage("finalization"):
            print(f"[WORKFLOW] Executing finalization stage...")
            context = self._build_context(step=num_steps, dt=dt)
            self.workflow_executor.execute_finalization(context)

        return results

    def _build_context(self, step: int, dt: float) -> Dict[str, Any]:
        """
        Build execution context for workflow functions.
        Provides all the data that workflow functions might need.
        """
        return {
            'step': step,
            'dt': dt,
            'time': step * dt,
            'population': self.population,
            'simulator': self.simulator,
            'gene_network': self.gene_network,
            'config': self.config,
            'substance_concentrations': self.simulator.get_substance_concentrations(),
        }

    def _export_cell_states(self, step: int):
        """Export cell states and substance fields based on domain dimensions."""
        # Determine export format based on domain dimensions
        if self.config.domain.dimensions == 2:
            print(f"\n[CSV] Exporting 2D simulation checkpoint at step {step}...")
            try:
                import sys
                import os
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
                from csv_export import export_microc_csv_checkpoint

                # Export unified checkpoint (cells + substances in one file)
                csv_output_dir = self.config.output_dir / "csv_checkpoints"
                csv_file = export_microc_csv_checkpoint(
                    population=self.population,
                    simulator=self.simulator,
                    output_dir=str(csv_output_dir),
                    step=step,
                    cell_size_um=self.config.output.cell_size_um
                )

                if csv_file:
                    print(f"[+] Checkpoint exported successfully")
                else:
                    print(f"[!] CSV checkpoint export failed")

            except Exception as e:
                print(f"[!] CSV export failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            # 3D VTK export
            print(f"\n[VTK] Exporting 3D simulation checkpoint at step {step}...")
            try:
                import sys
                import os
                sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
                from vtk_export import export_microc_vtk_checkpoint

                # Export unified checkpoint (cells + substances in organized folder)
                vtk_output_dir = self.config.output_dir / "vtk_checkpoints"
                checkpoint_folder = export_microc_vtk_checkpoint(
                    population=self.population,
                    simulator=self.simulator,
                    output_dir=str(vtk_output_dir),
                    step=step,
                    cell_size_um=self.config.output.cell_size_um
                )

                if checkpoint_folder:
                    print(f"[+] Checkpoint exported successfully")
                else:
                    print(f"[!] VTK checkpoint export failed")

            except Exception as e:
                print(f"[!] VTK export failed: {e}")
                import traceback
                traceback.print_exc()


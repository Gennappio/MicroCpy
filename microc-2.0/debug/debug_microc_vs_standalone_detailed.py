#!/usr/bin/env python3
"""
Detailed comparison between MicroC and standalone FiPy implementations.
This script will run both and compare ALL inputs and outputs systematically.
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import FiPy
try:
    from fipy import Grid2D, CellVariable, DiffusionTerm, ImplicitSourceTerm
    from fipy.solvers.scipy import LinearGMRESSolver as Solver
    print("[+] FiPy available")
except ImportError:
    print("[!] FiPy not available")
    exit(1)

# Import MicroC components
from config.config import MicroCConfig
from core.domain import MeshManager
from simulation.multi_substance_simulator import MultiSubstanceSimulator
from biology.population import CellPopulation
from biology.gene_network import BooleanNetwork

def run_standalone_fipy():
    """Run the standalone FiPy implementation"""
    print("\n" + "="*60)
    print(" RUNNING STANDALONE FIPY")
    print("="*60)
    
    # EXACT parameters from standalone script
    domain_size = 1500e-6  # 1500 um in meters
    grid_size = (75, 75)   # 75x75 grid
    nx, ny = grid_size
    
    # MicroC lactate parameters
    diffusion_coeff = 1.8e-10  # m/s
    initial_value = 1.0        # mM
    boundary_value = 1.0       # mM
    cell_height = 20e-6        # 20 um
    
    print(f" Domain: {domain_size*1e6:.0f} x {domain_size*1e6:.0f} um")
    print(f" Grid: {nx} x {ny}")
    print(f" Cell height: {cell_height*1e6:.1f} um")
    print(f" Diffusion coeff: {diffusion_coeff:.2e} m/s")
    print(f" Initial lactate: {initial_value} mM")
    print(f" Boundary lactate: {boundary_value} mM")
    
    # Calculate mesh spacing
    dx = domain_size / nx
    dy = domain_size / ny
    
    print(f" Grid spacing: {dx*1e6:.1f} x {dy*1e6:.1f} um")
    
    # Create FiPy mesh
    mesh = Grid2D(dx=dx, dy=dy, nx=nx, ny=ny)
    
    # Create lactate variable
    lactate = CellVariable(name="Lactate", mesh=mesh, value=initial_value)
    
    # Set boundary conditions
    lactate.constrain(boundary_value, mesh.facesTop | mesh.facesBottom | 
                     mesh.facesLeft | mesh.facesRight)
    
    # Place 1 cell in center
    center_x = nx // 2
    center_y = ny // 2
    
    cells = [{
        'grid_x': center_x,
        'grid_y': center_y,
        'id': 0
    }]
    
    print(f"[+] Placed {len(cells)} cells at center ({center_x}, {center_y})")
    
    # Create source field
    source_field = np.zeros(nx * ny)
    
    # Volume calculation
    mesh_cell_volume = dx * dy * cell_height
    twodimensional_adjustment_coefficient = 1.0
    
    print(f"[SEARCH] Volume calculation:")
    print(f"   dx: {dx:.2e} m")
    print(f"   dy: {dy:.2e} m")
    print(f"   cell_height: {cell_height:.2e} m")
    print(f"   mesh_cell_volume: {mesh_cell_volume:.2e} m")
    print(f"   2D adjustment: {twodimensional_adjustment_coefficient}")
    
    # Lactate production rate (positive = production)
    lactate_production_rate = 2.8e-2  # mM/s
    
    print(f"[SEARCH] Lactate production rate: {lactate_production_rate:.2e} mM/s")
    
    for cell in cells:
        x = cell['grid_x']
        y = cell['grid_y']
        
        if 0 <= x < nx and 0 <= y < ny:
            # Convert to FiPy index (column-major order)
            fipy_idx = x * ny + y
            source_field[fipy_idx] = lactate_production_rate
    
    print(f"[SEARCH] Source field stats:")
    print(f"   Non-zero cells: {np.count_nonzero(source_field)}")
    print(f"   Min rate: {np.min(source_field):.2e} mM/s")
    print(f"   Max rate: {np.max(source_field):.2e} mM/s")
    
    # Create source variable
    source_var = CellVariable(mesh=mesh, value=source_field)
    
    # Create equation: DiffusionTerm(D) == -source_var
    equation = DiffusionTerm(coeff=diffusion_coeff) == -source_var
    
    print("\n[RUN] Solving steady-state diffusion equation...")
    
    # Solve
    solver = Solver(iterations=1000, tolerance=1e-6)
    
    try:
        res = equation.solve(var=lactate, solver=solver)
        if res is not None:
            print(f"[+] FiPy solver finished. Final residual: {res:.2e}")
        else:
            print(f"[+] FiPy solver finished.")
    except Exception as e:
        print(f" Error during solve: {e}")
        return None
    
    # Get results
    lactate_concentrations = lactate.value.reshape((nx, ny), order='F')
    
    print(f"\n[CHART] STANDALONE RESULTS:")
    print(f"   Lactate range: {np.min(lactate_concentrations):.6f} - {np.max(lactate_concentrations):.6f} mM")
    print(f"   Initial value: {initial_value} mM")
    print(f"   Max increase: {np.max(lactate_concentrations) - initial_value:.6f} mM")
    print(f"   Center value: {lactate_concentrations[center_x, center_y]:.6f} mM")
    
    return {
        'concentrations': lactate_concentrations,
        'domain_size': domain_size,
        'grid_size': grid_size,
        'diffusion_coeff': diffusion_coeff,
        'initial_value': initial_value,
        'boundary_value': boundary_value,
        'cell_height': cell_height,
        'source_rate': lactate_production_rate,
        'center_pos': (center_x, center_y),
        'mesh_cell_volume': mesh_cell_volume
    }

def run_microc():
    """Run MicroC implementation"""
    print("\n" + "="*60)
    print(" RUNNING MICROC")
    print("="*60)
    
    # Load config
    config_path = Path("tests/jayatilake_experiment/jayatilake_experiment_config.yaml")
    config = MicroCConfig.load_from_yaml(config_path)
    
    print(f"[FOLDER] Loaded config: {config_path}")
    print(f" Domain: {config.domain.size_x.value}x{config.domain.size_y.value} {config.domain.size_x.unit}")
    print(f" Grid: {config.domain.nx}x{config.domain.ny}")
    print(f" Cell height: {config.domain.cell_height.value} {config.domain.cell_height.unit}")
    
    # Create components
    mesh_manager = MeshManager(config.domain)
    simulator = MultiSubstanceSimulator(config, mesh_manager)
    gene_network = BooleanNetwork(config=config)
    population = CellPopulation(
        grid_size=(config.domain.nx, config.domain.ny),
        gene_network=gene_network,
        custom_functions_module="tests/jayatilake_experiment/jayatilake_experiment_custom_functions.py",
        config=config
    )
    
    print(f"[+] Created components")
    
    # Add single cell at center
    center_x = config.domain.nx // 2
    center_y = config.domain.ny // 2
    success = population.add_cell((center_x, center_y), phenotype="Proliferation")
    
    print(f"[+] Added cell at center ({center_x}, {center_y}): {success}")
    print(f"   Total cells: {len(population.state.cells)}")
    
    # Get initial concentrations
    current_concentrations = simulator.get_substance_concentrations()
    
    # Get reactions from population
    substance_reactions = population.get_substance_reactions(current_concentrations)
    
    print(f"\n[SEARCH] MICROC INPUTS:")
    print(f"   Substance reactions: {len(substance_reactions)} positions")
    
    for position, reactions in substance_reactions.items():
        print(f"   Position {position}: {reactions}")
        if 'Lactate' in reactions:
            lactate_rate = reactions['Lactate']
            print(f"   [+] Lactate reaction: {lactate_rate:.2e} mol/s/cell")
            
            # Calculate expected mM/s rate
            dx = config.domain.size_x.meters / config.domain.nx
            dy = config.domain.size_y.meters / config.domain.ny
            cell_height = config.domain.cell_height.meters
            mesh_cell_volume = dx * dy * cell_height
            
            volumetric_rate = lactate_rate / mesh_cell_volume
            final_rate = volumetric_rate * 1000.0
            print(f"   Expected mM/s rate: {final_rate:.2e} mM/s")
        else:
            print(f"   [!] Lactate reaction NOT found!")
    
    # Update diffusion
    print(f"\n[RUN] Running MicroC diffusion update...")
    simulator.update(substance_reactions)
    
    # Get results
    lactate_state = simulator.state.substances['Lactate']
    lactate_concentrations = lactate_state.concentrations
    
    print(f"\n[CHART] MICROC RESULTS:")
    print(f"   Lactate range: {np.min(lactate_concentrations):.6f} - {np.max(lactate_concentrations):.6f} mM")
    print(f"   Initial value: {config.substances['Lactate'].initial_value.value} mM")
    print(f"   Max increase: {np.max(lactate_concentrations) - config.substances['Lactate'].initial_value.value:.6f} mM")
    print(f"   Center value: {lactate_concentrations[center_y, center_x]:.6f} mM")  # Note: y,x order
    
    return {
        'concentrations': lactate_concentrations,
        'config': config,
        'center_pos': (center_x, center_y),
        'substance_reactions': substance_reactions
    }

def compare_results(standalone_result, microc_result):
    """Compare the results systematically"""
    print("\n" + "="*60)
    print("[SEARCH] DETAILED COMPARISON")
    print("="*60)
    
    # Compare parameters
    print(f"\n PARAMETER COMPARISON:")
    
    standalone_domain = standalone_result['domain_size'] * 1e6
    microc_domain = microc_result['config'].domain.size_x.value
    print(f"   Domain size: Standalone={standalone_domain:.0f}um, MicroC={microc_domain:.0f}um")
    
    standalone_grid = standalone_result['grid_size']
    microc_grid = (microc_result['config'].domain.nx, microc_result['config'].domain.ny)
    print(f"   Grid size: Standalone={standalone_grid}, MicroC={microc_grid}")
    
    standalone_diff = standalone_result['diffusion_coeff']
    microc_diff = microc_result['config'].substances['Lactate'].diffusion_coeff
    print(f"   Diffusion coeff: Standalone={standalone_diff:.2e}, MicroC={microc_diff:.2e}")
    
    standalone_init = standalone_result['initial_value']
    microc_init = microc_result['config'].substances['Lactate'].initial_value.value
    print(f"   Initial value: Standalone={standalone_init:.1f}mM, MicroC={microc_init:.1f}mM")
    
    # Compare source terms
    print(f"\n[SEARCH] SOURCE TERM COMPARISON:")
    standalone_rate = standalone_result['source_rate']
    print(f"   Standalone rate: {standalone_rate:.2e} mM/s (hardcoded)")
    
    if microc_result['substance_reactions']:
        for pos, reactions in microc_result['substance_reactions'].items():
            if 'Lactate' in reactions:
                microc_rate_mol = reactions['Lactate']
                
                # Convert to mM/s
                dx = microc_result['config'].domain.size_x.meters / microc_result['config'].domain.nx
                dy = microc_result['config'].domain.size_y.meters / microc_result['config'].domain.ny
                cell_height = microc_result['config'].domain.cell_height.meters
                mesh_cell_volume = dx * dy * cell_height
                
                volumetric_rate = microc_rate_mol / mesh_cell_volume
                microc_rate_mm = volumetric_rate * 1000.0
                
                print(f"   MicroC rate: {microc_rate_mol:.2e} mol/s/cell -> {microc_rate_mm:.2e} mM/s")
                print(f"   Rate ratio (MicroC/Standalone): {microc_rate_mm/standalone_rate:.2e}")
                
                if microc_rate_mol < 0:
                    print(f"   [!] PROBLEM: MicroC has CONSUMPTION (negative), Standalone has PRODUCTION (positive)")
                elif abs(microc_rate_mm - standalone_rate) > 1e-3:
                    print(f"   [!] PROBLEM: Rates differ significantly")
                else:
                    print(f"   [+] Rates match well")
    
    # Compare concentration results
    print(f"\n[CHART] CONCENTRATION COMPARISON:")
    standalone_conc = standalone_result['concentrations']
    microc_conc = microc_result['concentrations']
    
    standalone_center = standalone_conc[standalone_result['center_pos'][0], standalone_result['center_pos'][1]]
    microc_center = microc_conc[microc_result['center_pos'][1], microc_result['center_pos'][0]]  # Note: y,x order
    
    print(f"   Standalone center: {standalone_center:.6f} mM")
    print(f"   MicroC center: {microc_center:.6f} mM")
    print(f"   Center difference: {abs(standalone_center - microc_center):.6f} mM")
    
    standalone_range = np.max(standalone_conc) - np.min(standalone_conc)
    microc_range = np.max(microc_conc) - np.min(microc_conc)
    
    print(f"   Standalone range: {standalone_range:.6f} mM")
    print(f"   MicroC range: {microc_range:.6f} mM")
    print(f"   Range ratio (MicroC/Standalone): {microc_range/standalone_range:.2e}")
    
    if microc_range < 1e-6:
        print(f"   [!] PROBLEM: MicroC shows essentially no gradients!")
    elif abs(microc_range - standalone_range) / standalone_range > 0.1:
        print(f"   [!] PROBLEM: Concentration ranges differ significantly")
    else:
        print(f"   [+] Concentration ranges match well")

def main():
    """Main comparison function"""
    print(" DETAILED MICROC vs STANDALONE COMPARISON")
    print("=" * 80)
    
    # Run standalone
    standalone_result = run_standalone_fipy()
    if standalone_result is None:
        print("[!] Standalone failed")
        return
    
    # Run MicroC
    microc_result = run_microc()
    
    # Compare
    compare_results(standalone_result, microc_result)
    
    print("\n" + "="*80)
    print("[TARGET] SUMMARY:")
    print("   Check the comparison above for specific issues.")
    print("   Key things to look for:")
    print("   1. Source term sign (production vs consumption)")
    print("   2. Source term magnitude")
    print("   3. Concentration gradients")
    print("=" * 80)

if __name__ == "__main__":
    main()

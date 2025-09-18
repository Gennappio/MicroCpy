#!/usr/bin/env python3
"""
Comprehensive lactate tracking system for MicroC.
Instruments the code to track lactate values at every step.
"""

import sys
import os
sys.path.append('src')
sys.path.append('tests/jayatilake_experiment')

import numpy as np
from typing import Dict, Any, List, Tuple
import yaml
from pathlib import Path

class LactateTracker:
    """Tracks lactate values throughout MicroC simulation"""
    
    def __init__(self):
        self.tracking_data = []
        self.step_count = 0
        
    def track(self, location: str, lactate_data: Any, extra_info: str = ""):
        """Track lactate data at a specific location"""
        
        entry = {
            'step': self.step_count,
            'location': location,
            'extra_info': extra_info,
            'timestamp': len(self.tracking_data)
        }
        
        # Extract lactate information based on data type
        if isinstance(lactate_data, np.ndarray):
            entry.update({
                'type': 'array',
                'shape': lactate_data.shape,
                'min': float(np.min(lactate_data)),
                'max': float(np.max(lactate_data)),
                'mean': float(np.mean(lactate_data)),
                'sum': float(np.sum(lactate_data)),
                'nonzero_count': int(np.count_nonzero(lactate_data))
            })
        elif isinstance(lactate_data, dict):
            if 'Lactate' in lactate_data:
                lactate_val = lactate_data['Lactate']
                entry.update({
                    'type': 'dict_lactate',
                    'lactate_value': float(lactate_val),
                    'dict_keys': list(lactate_data.keys())
                })
            else:
                entry.update({
                    'type': 'dict_no_lactate',
                    'dict_keys': list(lactate_data.keys())
                })
        elif isinstance(lactate_data, (int, float)):
            entry.update({
                'type': 'scalar',
                'value': float(lactate_data)
            })
        else:
            entry.update({
                'type': str(type(lactate_data)),
                'str_repr': str(lactate_data)[:100]
            })
        
        self.tracking_data.append(entry)
        
        # Print important changes
        if 'lactate' in location.lower() or 'Lactate' in str(lactate_data):
            print(f"🔍 LACTATE TRACK [{self.step_count}] {location}: {entry.get('lactate_value', entry.get('max', 'N/A'))} {extra_info}")
    
    def next_step(self):
        """Increment step counter"""
        self.step_count += 1
        print(f"\n📍 STEP {self.step_count}")
    
    def save_report(self, filename: str = "lactate_tracking_report.txt"):
        """Save detailed tracking report"""
        with open(filename, 'w') as f:
            f.write("LACTATE TRACKING REPORT\n")
            f.write("=" * 50 + "\n\n")
            
            for entry in self.tracking_data:
                f.write(f"[{entry['timestamp']:03d}] Step {entry['step']} - {entry['location']}\n")
                f.write(f"    Type: {entry['type']}\n")
                
                if entry['type'] == 'array':
                    f.write(f"    Shape: {entry['shape']}\n")
                    f.write(f"    Min/Max/Mean: {entry['min']:.6f} / {entry['max']:.6f} / {entry['mean']:.6f}\n")
                    f.write(f"    Sum: {entry['sum']:.6f}, NonZero: {entry['nonzero_count']}\n")
                elif entry['type'] == 'dict_lactate':
                    f.write(f"    Lactate Value: {entry['lactate_value']:.6f}\n")
                    f.write(f"    Dict Keys: {entry['dict_keys']}\n")
                elif entry['type'] == 'scalar':
                    f.write(f"    Value: {entry['value']:.6f}\n")
                
                if entry['extra_info']:
                    f.write(f"    Info: {entry['extra_info']}\n")
                f.write("\n")
        
        print(f"📄 Tracking report saved to: {filename}")

# Global tracker instance
tracker = LactateTracker()

def instrument_microc_for_lactate_tracking():
    """Add tracking instrumentation to MicroC components"""
    
    print("🔧 INSTRUMENTING MICROC FOR LACTATE TRACKING")
    print("=" * 60)
    
    # Patch the multi-substance simulator
    try:
        from simulation.multi_substance_simulator import MultiSubstanceSimulator
        
        # Store original methods
        original_update = MultiSubstanceSimulator.update
        original_create_source_field = MultiSubstanceSimulator._create_source_field_from_reactions
        
        def tracked_update(self, substance_reactions):
            tracker.track("MultiSubstanceSimulator.update - INPUT", substance_reactions, "substance_reactions dict")
            
            # Check lactate in reactions
            lactate_reactions = {}
            for pos, reactions in substance_reactions.items():
                if 'Lactate' in reactions:
                    lactate_reactions[pos] = reactions['Lactate']
            
            if lactate_reactions:
                tracker.track("MultiSubstanceSimulator.update - LACTATE_REACTIONS", lactate_reactions, f"{len(lactate_reactions)} cells with lactate reactions")
            
            # Call original
            result = original_update(self, substance_reactions)
            
            # Track lactate state after update
            if 'Lactate' in self.state.substances:
                lactate_state = self.state.substances['Lactate']
                tracker.track("MultiSubstanceSimulator.update - OUTPUT", lactate_state.concentrations, "lactate concentrations after update")
            
            return result
        
        def tracked_create_source_field(self, substance_name, substance_reactions):
            result = original_create_source_field(self, substance_name, substance_reactions)
            
            if substance_name == 'Lactate':
                tracker.track(f"MultiSubstanceSimulator._create_source_field - {substance_name}", result, "source field array")
            
            return result
        
        # Apply patches
        MultiSubstanceSimulator.update = tracked_update
        MultiSubstanceSimulator._create_source_field_from_reactions = tracked_create_source_field
        
        print("✅ Patched MultiSubstanceSimulator")
        
    except ImportError as e:
        print(f"❌ Could not patch MultiSubstanceSimulator: {e}")
    
    # Patch the custom metabolism function
    try:
        from jayatilake_experiment_custom_functions import calculate_cell_metabolism
        
        # Store original
        original_metabolism = calculate_cell_metabolism
        
        def tracked_metabolism(local_environment, cell_state, config=None):
            # Track inputs
            if 'Lactate' in local_environment:
                tracker.track("calculate_cell_metabolism - INPUT_ENV", local_environment['Lactate'], "local lactate concentration")
            
            # Call original
            result = original_metabolism(local_environment, cell_state, config)
            
            # Track output
            if 'Lactate' in result:
                tracker.track("calculate_cell_metabolism - OUTPUT", result['Lactate'], "lactate reaction rate")
            
            return result
        
        # Apply patch (this is tricky - we need to modify the module)
        import jayatilake_experiment_custom_functions
        jayatilake_experiment_custom_functions.calculate_cell_metabolism = tracked_metabolism
        
        print("✅ Patched calculate_cell_metabolism")
        
    except ImportError as e:
        print(f"❌ Could not patch calculate_cell_metabolism: {e}")

def run_tracked_simulation_step():
    """Run a single simulation step with full lactate tracking"""
    
    print("\n🚀 RUNNING TRACKED SIMULATION STEP")
    print("=" * 50)
    
    # Import MicroC components
    try:
        from config.config import MicroCConfig
        from core.domain import MeshManager
        from simulation.multi_substance_simulator import MultiSubstanceSimulator
        from biology.population import Population
        
        # Load config
        config_path = "tests/jayatilake_experiment/jayatilake_experiment_config.yaml"
        config = MicroCConfig.from_yaml(config_path)
        tracker.track("CONFIG_LOADED", config.substances['Lactate'].initial_value.value, "initial lactate from config")
        
        # Create mesh manager
        mesh_manager = MeshManager(config.domain)
        tracker.track("MESH_CREATED", mesh_manager.grid_size, "mesh grid size")
        
        # Create substance simulator
        substance_sim = MultiSubstanceSimulator(config, mesh_manager)
        tracker.track("SUBSTANCE_SIM_CREATED", substance_sim.state.substances['Lactate'].concentrations, "initial lactate field")
        
        # Create population
        population = Population(config, mesh_manager)
        tracker.track("POPULATION_CREATED", len(population.cells), "number of cells created")
        
        # Initialize cells
        population.initialize_cells()
        tracker.track("CELLS_INITIALIZED", len(population.cells), "cells after initialization")
        
        # Get cell reactions
        cell_reactions = population.get_substance_reactions()
        tracker.track("CELL_REACTIONS", cell_reactions, "reactions from population")
        
        # Update substances
        tracker.next_step()
        substance_sim.update(cell_reactions)
        
        # Final lactate state
        final_lactate = substance_sim.state.substances['Lactate'].concentrations
        tracker.track("FINAL_LACTATE_STATE", final_lactate, "final lactate concentrations")
        
        print(f"\n📊 SIMULATION STEP COMPLETE")
        print(f"   Initial lactate max: {np.max(substance_sim.state.substances['Lactate'].concentrations):.6f}")
        print(f"   Final lactate max: {np.max(final_lactate):.6f}")
        
        return {
            'config': config,
            'substance_sim': substance_sim,
            'population': population,
            'final_lactate': final_lactate
        }
        
    except Exception as e:
        print(f"❌ Error in tracked simulation: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🔍 LACTATE TRACKING SYSTEM")
    print("=" * 60)
    
    # Instrument MicroC
    instrument_microc_for_lactate_tracking()
    
    # Run tracked simulation
    results = run_tracked_simulation_step()
    
    # Save tracking report
    tracker.save_report()
    
    print(f"\n🎯 TRACKING COMPLETE")
    print(f"   Total tracking points: {len(tracker.tracking_data)}")
    print(f"   Check lactate_tracking_report.txt for details")
    
    if results:
        final_lactate = results['final_lactate']
        print(f"   Final lactate range: {np.min(final_lactate):.6f} - {np.max(final_lactate):.6f}")
        
        if np.max(final_lactate) > np.min(final_lactate) + 0.001:
            print(f"   ✅ Lactate variation detected!")
        else:
            print(f"   ❌ No significant lactate variation")

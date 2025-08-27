#!/usr/bin/env python3
"""
Generate 16 config files for systematic combination testing.
Each config has a single cell with different substance concentrations.
"""

import os
import yaml
from pathlib import Path

def create_base_config():
    """Create the base configuration that will be modified for each combination."""
    return {
        # Jayatilake Metabolic Symbiosis Experiment Configuration - SINGLE CELL VERSION
        # Based on: Jayatilake et al. "A computational model of metabolic symbiosis in cancer"
        # Modified for single cell testing with fixed substance concentrations
        
        # Domain configuration - small domain for single cell
        "domain": {
            "size_x": 40.0,  # Single cell domain
            "size_x_unit": "um",
            "size_y": 40.0,
            "size_y_unit": "um", 
            "nx": 1,  # 1x1 grid = single zone
            "ny": 1,
            "dimensions": 2,
            "cell_height": 40.0,
            "cell_height_unit": "um"
        },
        
        # Time configuration - SHORT simulation for testing
        "time": {
            "dt": 0.1,
            "end_time": 5.0,  # SHORT: Only 5 time units (50 steps)
            "diffusion_step": 999999,  # DISABLE diffusion (fixed concentrations)
            "intracellular_step": 1,   # Update gene networks every step
            "intercellular_step": 999999  # DISABLE intercellular updates
        },
        
        # Diffusion solver configuration - DISABLED
        "diffusion": {
            "max_iterations": 1,
            "tolerance": 1e-6,
            "solver_type": "steady_state",
            "twodimensional_adjustment_coefficient": 1.0
        },
        
        # Output configuration - More frequent for short simulation
        "output": {
            "save_data_interval": 5,   # Save every 5 steps
            "save_plots_interval": 5,  # Plot every 5 steps
            "save_final_plots": True,
            "save_initial_plots": True,
            "status_print_interval": 5  # Status every 5 steps
        },
        
        # Substances - SAME AS JAYATILAKE but with DISABLED DIFFUSION
        "substances": {
            "Oxygen": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 0.07,   # Will be overridden per combination
                "boundary_value": 0.07,
                "boundary_type": "fixed",
                "unit": "mM"
            },
            "Glucose": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 5.0,    # Will be overridden per combination
                "boundary_value": 5.0,
                "boundary_type": "fixed",
                "unit": "mM"
            },
            "Lactate": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 1.0,    # Will be overridden per combination
                "boundary_value": 1.0,
                "boundary_type": "fixed",
                "unit": "mM"
            },
            "H": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 4.0e-5,
                "boundary_value": 4.0e-5,
                "boundary_type": "fixed",
                "unit": "mM"
            },
            "FGF": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 5.0e-7,
                "boundary_value": 5.0e-7,
                "boundary_type": "fixed",
                "unit": "uM"
            },
            "EGF": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 5.0e-7,
                "boundary_value": 5.0e-7,
                "boundary_type": "fixed",
                "unit": "uM"
            },
            "TGFA": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 5.0e-7, # Will be overridden per combination
                "boundary_value": 5.0e-7,
                "boundary_type": "fixed",
                "unit": "uM"
            },
            "VEGF": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 5.0e-7,
                "boundary_value": 5.0e-7,
                "boundary_type": "fixed",
                "unit": "uM"
            },
            "HGF": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 5.0e-7,
                "boundary_value": 5.0e-7,
                "boundary_type": "fixed",
                "unit": "uM"
            },
            "EGFRD": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 0.0e-3,
                "boundary_value": 0.0e-3,
                "boundary_type": "fixed",
                "unit": "mM"
            },
            "FGFRD": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 0.0e-3,
                "boundary_value": 0.0e-3,
                "boundary_type": "fixed",
                "unit": "mM"
            },
            "GI": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 0.000,
                "boundary_value": 0.000,
                "boundary_type": "fixed",
                "unit": "mM"
            },
            "cMETD": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 0.0e-3,
                "boundary_value": 0.0e-3,
                "boundary_type": "fixed",
                "unit": "mM"
            },
            "pH": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 7.4,
                "boundary_value": 7.4,
                "boundary_type": "fixed",
                "unit": "pH"
            },
            "MCT1D": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 0.0e-6,
                "boundary_value": 0.0e-6,
                "boundary_type": "fixed",
                "unit": "uM"
            },
            "GLUT1D": {
                "diffusion_coeff": 0.0,  # DISABLED
                "production_rate": 0.0,
                "uptake_rate": 0.0,      # DISABLED
                "initial_value": 0.0e-6,
                "boundary_value": 0.0e-6,
                "boundary_type": "fixed",
                "unit": "uM"
            }
        }
    }

def add_remaining_config(config, combination_id):
    """Add the remaining configuration sections."""
    # Gene input associations - SAME AS JAYATILAKE
    config["associations"] = {
        "Oxygen": "Oxygen_supply",
        "Glucose": "Glucose_supply",
        "Lactate": "MCT1_stimulus",
        "H": "Proton_level",
        "FGF": "FGFR_stimulus",
        "EGF": "EGFR_stimulus",
        "HGF": "cMET_stimulus",
        "EGFRD": "EGFRI",
        "FGFRD": "FGFRI",
        "GI": "Growth_Inhibitor",
        "cMETD": "cMETI",
        "MCT1D": "MCT1I",
        "GLUT1D": "GLUT1I",
        "TGFA": "EGFR_stimulus"
    }

    # Gene input thresholds - SAME AS JAYATILAKE
    config["thresholds"] = {
        "Oxygen_supply": {"initial": 0.07, "threshold": 0.022},
        "Glucose_supply": {"initial": 5.0, "threshold": 4.0},
        "MCT1_stimulus": {"initial": 1.0, "threshold": 1.5},
        "Proton_level": {"initial": 4.0e-5, "threshold": 8.0e-5},
        "FGFR_stimulus": {"initial": 0.0, "threshold": 1.0e-6},
        "EGFR_stimulus": {"initial": 0.0, "threshold": 1.0e-6},
        "cMET_stimulus": {"initial": 2.0e-6, "threshold": 1.0e-6},
        "Growth_Inhibitor": {"initial": 0.0, "threshold": 0.00005},
        "DNA_damage": {"initial": 0.0, "threshold": 0.5},
        "TGFBR_stimulus": {"initial": 0.0, "threshold": 1.0e-6},
        "GLUT1I": {"initial": 0.0, "threshold": 4.0e-6},
        "GLUT1D": {"initial": 0.0, "threshold": 0.5},
        "EGFRI": {"initial": 0.0, "threshold": 0.005},
        "FGFRI": {"initial": 0.0, "threshold": 0.005},
        "cMETI": {"initial": 0.0, "threshold": 0.005},
        "MCT1I": {"initial": 0.0, "threshold": 1.7e-5},
        "MCT4I": {"initial": 0.0, "threshold": 1.0},
        "pH_min": {"initial": 8.0, "threshold": 6.0}
    }

    # Gene network configuration - SAME AS JAYATILAKE
    config["gene_network"] = {
        "bnd_file": "tests/jayatilake_experiment/jaya_microc.bnd",
        "propagation_steps": 50,
        "random_initialization": True,
        "output_nodes": ["Proliferation", "Apoptosis", "Growth_Arrest", "Necrosis"],
        "nodes": {
            "Oxygen_supply": {"is_input": True, "default_state": True},
            "Glucose_supply": {"is_input": True, "default_state": True},
            "MCT1_stimulus": {"is_input": True, "default_state": True},
            "Proton_level": {"is_input": True, "default_state": False},
            "FGFR_stimulus": {"is_input": True, "default_state": False},
            "EGFR_stimulus": {"is_input": True, "default_state": False},
            "cMET_stimulus": {"is_input": True, "default_state": False},
            "Growth_Inhibitor": {"is_input": True, "default_state": False},
            "DNA_damage": {"is_input": True, "default_state": False},
            "TGFBR_stimulus": {"is_input": True, "default_state": False},
            "GLUT1I": {"is_input": True, "default_state": False},
            "GLUT1D": {"is_input": True, "default_state": False},
            "EGFRI": {"is_input": True, "default_state": False},
            "FGFRI": {"is_input": True, "default_state": False},
            "cMETI": {"is_input": True, "default_state": False},
            "MCT1I": {"is_input": True, "default_state": False},
            "MCT4I": {"is_input": True, "default_state": False}
        }
    }

    # Environment configuration
    config["environment"] = {"ph": 7.4}

    # Direct top-level parameters
    config["cell_cycle_time"] = 240
    config["max_cell_age"] = 500.0

    # Custom parameters - SAME AS JAYATILAKE + SINGLE CELL MODIFICATIONS
    config["custom_parameters"] = {
        "max_atp": 30,
        "atp_threshold": 0.8,
        "glyco_oxygen_ratio": 0.1,
        "proton_coefficient": 0.01,
        "glucose_factor": 2,
        "KG": 0.5,
        "KO2": 0.01,
        "KL": 1.0,
        "the_optimal_oxygen": 0.005,
        "the_optimal_glucose": 0.04,
        "the_optimal_lactate": 0.04,
        "oxygen_vmax": 3.0e-17,
        "glucose_vmax": 3.0e-15,
        "mu_o2": 1.0e-15,
        "A0": 30.0,
        "beta": 0.1,
        "K_glyco": 0.5,
        "tgfa_consumption_rate": 2.0e-20,
        "tgfa_production_rate": 2.0e-17,
        "hgf_consumption_rate": 2.0e-18,
        "hgf_production_rate": 0.0,
        "fgf_consumption_rate": 2.0e-18,
        "fgf_production_rate": 0.0,
        "min_glucose_for_glycolysis": 0.1,
        "min_oxygen_for_oxphos": 0.01,
        "min_lactate_for_consumption": 0.1,
        "glucose_depletion_threshold": 0.05,
        "lactate_saturation_threshold": 8.0,
        "oxygen_switch_threshold": 0.015,
        "ph_inhibition_threshold": 1.0e-4,
        "necrosis_threshold_oxygen": 0.011,
        "necrosis_threshold_glucose": 0.23,
        "initial_cell_count": 1,  # SINGLE CELL
        "maximum_cell_count": 1,  # NO GROWTH
        "shedding_rate": 0.0,     # NO SHEDDING
        "shedding_starting_time": 0
    }

    # Output directories - unique per combination
    config["output_dir"] = f"results/multitest/combination_{combination_id:02d}"
    config["plots_dir"] = f"plots/multitest/combination_{combination_id:02d}"
    config["data_dir"] = f"data/multitest/combination_{combination_id:02d}"
    # NO custom functions - use default cell placement for single cell

    return config

if __name__ == "__main__":
    # Define the 4 key substances and their high/low values
    key_substances = {
        "Oxygen": {"high": 0.06, "low": 0.01},      # Above/below threshold 0.022
        "Lactate": {"high": 3.0, "low": 0.5},       # Above/below threshold 1.5
        "Glucose": {"high": 6.0, "low": 2.0},       # Above/below threshold 4.0
        "TGFA": {"high": 2.0e-6, "low": 5.0e-7}     # Above/below threshold 1.0e-6
    }
    
    print("[TARGET] Generating 16 config files for systematic combination testing...")
    print("[FOLDER] Each config has a single cell with different substance concentrations")
    
    # Generate all 16 combinations (2^4)
    for combination_id in range(16):
        print(f"\n[NOTE] Creating config {combination_id:02d}...")
        
        # Create base config
        config = create_base_config()
        
        # Determine high/low states for this combination
        oxygen_high = bool((combination_id >> 0) & 1)
        lactate_high = bool((combination_id >> 1) & 1)
        glucose_high = bool((combination_id >> 2) & 1)
        tgfa_high = bool((combination_id >> 3) & 1)
        
        # Set concentrations based on combination
        config["substances"]["Oxygen"]["initial_value"] = key_substances["Oxygen"]["high"] if oxygen_high else key_substances["Oxygen"]["low"]
        config["substances"]["Oxygen"]["boundary_value"] = config["substances"]["Oxygen"]["initial_value"]
        
        config["substances"]["Lactate"]["initial_value"] = key_substances["Lactate"]["high"] if lactate_high else key_substances["Lactate"]["low"]
        config["substances"]["Lactate"]["boundary_value"] = config["substances"]["Lactate"]["initial_value"]
        
        config["substances"]["Glucose"]["initial_value"] = key_substances["Glucose"]["high"] if glucose_high else key_substances["Glucose"]["low"]
        config["substances"]["Glucose"]["boundary_value"] = config["substances"]["Glucose"]["initial_value"]
        
        config["substances"]["TGFA"]["initial_value"] = key_substances["TGFA"]["high"] if tgfa_high else key_substances["TGFA"]["low"]
        config["substances"]["TGFA"]["boundary_value"] = config["substances"]["TGFA"]["initial_value"]
        
        # Add remaining config sections
        config = add_remaining_config(config, combination_id)
        
        # Print combination details
        oxygen_state = "HIGH" if oxygen_high else "LOW"
        lactate_state = "HIGH" if lactate_high else "LOW"
        glucose_state = "HIGH" if glucose_high else "LOW"
        tgfa_state = "HIGH" if tgfa_high else "LOW"
        
        print(f"    Combination {combination_id:02d}: O2={oxygen_state}, Lac={lactate_state}, Gluc={glucose_state}, TGFA={tgfa_state}")
        print(f"   [CHART] Values: O2={config['substances']['Oxygen']['initial_value']:.3f}, Lac={config['substances']['Lactate']['initial_value']:.1f}, Gluc={config['substances']['Glucose']['initial_value']:.1f}, TGFA={config['substances']['TGFA']['initial_value']:.1e}")
        
        # Save config file
        filename = f"config_{combination_id:02d}.yaml"
        filepath = Path(f"tests/multitest/{filename}")
        
        with open(filepath, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        print(f"   [+] Saved: {filename}")
    
    print(f"\n[SUCCESS] Successfully generated 16 config files!")
    print(f"[FOLDER] Location: tests/multitest/")
    print(f" Files: config_00.yaml to config_15.yaml")

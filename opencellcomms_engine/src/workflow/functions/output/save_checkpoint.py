"""Checkpoint functions for saving simulation state during the Loop.

These functions save gene network states, substance concentrations, and other
simulation data at configurable intervals during the simulation loop.
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json
from src.workflow.decorators import register_function
from src.interfaces.base import IConfig
from tools.csv_export import export_csv_cell_state, export_csv_substance_fields


@register_function(
    display_name="Save Gene Network Checkpoint",
    description="Save gene network states for all cells to JSON file",
    category="UTILITY",
    parameters=[
        {
            "name": "interval",
            "type": "INT",
            "description": "Save every N steps (0 = disabled, 1 = every step)",
            "default": 10,
        }
    ],
    outputs=[],
    cloneable=True
)
def save_gene_network_checkpoint(
    context: Dict[str, Any],
    interval: int = 10,
    **kwargs
) -> bool:
    """
    Save gene network states for all cells to a JSON file.

    Args:
        context: Workflow context containing population, step, config
        interval: Save every N steps (0 = disabled)
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful or skipped, False on error
    """
    try:
        step = context.get('step', 0)
        
        # Check interval
        if interval <= 0:
            return True  # Disabled
        if step % interval != 0:
            return True  # Not time to save
        
        population = context.get('population')
        config: Optional[IConfig] = context.get('config')
        
        if not population:
            print("[CHECKPOINT] No population in context - skipping")
            return True
        
        # Get output directory
        if 'output_dir' in context:
            output_dir = Path(context['output_dir'])
        else:
            output_dir = Path(config.output_dir) if config and hasattr(config, 'output_dir') else Path('results')
        
        checkpoint_dir = output_dir / "checkpoints" / "gene_networks"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # Collect gene network states
        gene_states = []
        for cell in population.state.cells:
            cell_state = {
                "cell_id": cell.cell_id,
                "position": list(cell.position),
            }
            
            # Get gene network states if available
            if hasattr(cell, 'gene_network') and cell.gene_network:
                try:
                    cell_state["gene_states"] = dict(cell.gene_network.get_all_states())
                except Exception:
                    cell_state["gene_states"] = {}
            elif hasattr(cell, 'gene_states'):
                cell_state["gene_states"] = dict(cell.gene_states) if cell.gene_states else {}
            else:
                cell_state["gene_states"] = {}
            
            # Get phenotype if available
            if hasattr(cell, 'phenotype'):
                cell_state["phenotype"] = str(cell.phenotype)
            
            gene_states.append(cell_state)
        
        # Save to file
        checkpoint_file = checkpoint_dir / f"gene_networks_step_{step:06d}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump({
                "step": step,
                "num_cells": len(gene_states),
                "cells": gene_states
            }, f, indent=2, default=str)
        
        print(f"[CHECKPOINT] Saved gene network states for {len(gene_states)} cells at step {step}")
        return True
        
    except Exception as e:
        print(f"[CHECKPOINT] Error saving gene network checkpoint: {e}")
        import traceback
        traceback.print_exc()
        return False


@register_function(
    display_name="Save Substance Checkpoint",
    description="Save substance concentration fields to files",
    category="UTILITY",
    parameters=[
        {
            "name": "interval",
            "type": "INT",
            "description": "Save every N steps (0 = disabled, 1 = every step)",
            "default": 10,
        },
        {
            "name": "format",
            "type": "STRING",
            "description": "Output format: 'csv' or 'npy'",
            "default": "csv",
            "options": ["csv", "npy"]
        }
    ],
    outputs=[],
    cloneable=True
)
def save_substance_checkpoint(
    context: Dict[str, Any],
    interval: int = 10,
    format: str = "csv",
    **kwargs
) -> bool:
    """
    Save substance concentration fields to files.

    Args:
        context: Workflow context containing simulator, step, config
        interval: Save every N steps (0 = disabled)
        format: Output format ('csv' or 'npy')
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful or skipped, False on error
    """
    try:
        step = context.get('step', 0)
        
        # Check interval
        if interval <= 0:
            return True
        if step % interval != 0:
            return True
        
        simulator = context.get('simulator')
        config: Optional[IConfig] = context.get('config')
        
        if not simulator:
            print("[CHECKPOINT] No simulator in context - skipping")
            return True

        # Get output directory
        if 'output_dir' in context:
            output_dir = Path(context['output_dir'])
        else:
            output_dir = Path(config.output_dir) if config and hasattr(config, 'output_dir') else Path('results')

        checkpoint_dir = output_dir / "checkpoints" / "substances"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Get substance concentrations
        try:
            concentrations = simulator.get_substance_concentrations()
        except Exception as e:
            print(f"[CHECKPOINT] Failed to get concentrations: {e}")
            return False

        saved_count = 0
        for name, field in concentrations.items():
            import numpy as np

            # Convert to numpy array if needed
            field_array = np.asarray(field)

            # Skip if field is empty or scalar (0D)
            if field_array.ndim == 0:
                print(f"[CHECKPOINT] Skipping {name}: scalar value (0D array)")
                continue

            if format == "npy":
                file_path = checkpoint_dir / f"{name}_step_{step:06d}.npy"
                np.save(file_path, field_array)
            else:  # csv
                file_path = checkpoint_dir / f"{name}_step_{step:06d}.csv"
                # Ensure at least 1D for savetxt
                if field_array.ndim == 1:
                    field_array = field_array.reshape(-1, 1)
                np.savetxt(file_path, field_array, delimiter=',', fmt='%.6e')
            saved_count += 1

        print(f"[CHECKPOINT] Saved {saved_count} substance fields at step {step}")
        return True

    except Exception as e:
        print(f"[CHECKPOINT] Error saving substance checkpoint: {e}")
        import traceback
        traceback.print_exc()
        return False


@register_function(
    display_name="Save Full Checkpoint",
    description="Save both gene networks and substances (combined checkpoint)",
    category="UTILITY",
    parameters=[
        {
            "name": "interval",
            "type": "INT",
            "description": "Save every N steps (0 = disabled, 1 = every step)",
            "default": 10,
        }
    ],
    outputs=[],
    cloneable=True
)
def save_full_checkpoint(
    context: Dict[str, Any],
    interval: int = 10,
    **kwargs
) -> bool:
    """
    Save both gene network states and substance fields.

    This is a convenience function that calls both save_gene_network_checkpoint
    and save_substance_checkpoint.

    Args:
        context: Workflow context
        interval: Save every N steps (0 = disabled)
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful or skipped, False on error
    """
    result1 = save_gene_network_checkpoint(context, interval=interval, **kwargs)
    result2 = save_substance_checkpoint(context, interval=interval, **kwargs)
    return result1 and result2


@register_function(
    display_name="Save Checkpoint (CSV Format)",
    description="Save checkpoint in unified CSV format compatible with read_checkpoint",
    category="UTILITY",
    parameters=[
        {
            "name": "interval",
            "type": "INT",
            "description": "Save every N steps (0 = disabled, 1 = every step)",
            "default": 10,
        },
        {
            "name": "save_substances",
            "type": "BOOL",
            "description": "Also save substance concentration fields",
            "default": True,
        }
    ],
    outputs=[],
    cloneable=True
)
def save_checkpoint(
    context: Dict[str, Any],
    interval: int = 10,
    save_substances: bool = True,
    **kwargs
) -> bool:
    """
    Save checkpoint in unified CSV format compatible with read_checkpoint.

    This function saves cell states (with gene states) to CSV format that can be
    read back by read_checkpoint. Optionally saves substance concentration fields.

    Args:
        context: Workflow context containing population, simulator, step, config
        interval: Save every N steps (0 = disabled)
        save_substances: Whether to also save substance concentration fields
        **kwargs: Additional parameters (ignored)

    Returns:
        True if successful or skipped, False on error
    """
    try:
        step = context.get('step', 0)

        # Check interval
        if interval <= 0:
            return True  # Disabled
        if step % interval != 0:
            return True  # Not time to save

        population = context.get('population')
        simulator = context.get('simulator')
        config: Optional[IConfig] = context.get('config')

        if not population:
            print("[CHECKPOINT] No population in context - skipping")
            return True

        # Get output directory
        if 'output_dir' in context:
            output_dir = Path(context['output_dir'])
        else:
            output_dir = Path(config.output_dir) if config and hasattr(config, 'output_dir') else Path('results')

        checkpoint_dir = output_dir / "checkpoints" / "csv"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # Get cell size from config
        cell_size_um = config.cell_size_um if config and hasattr(config, 'cell_size_um') else 20.0

        # Export cell state to CSV
        csv_file = export_csv_cell_state(population, str(checkpoint_dir), step, cell_size_um)

        if not csv_file:
            print(f"[CHECKPOINT] Failed to export cell state at step {step}")
            return False

        print(f"[CHECKPOINT] Saved CSV checkpoint at step {step}: {csv_file}")

        # Optionally save substance fields
        if save_substances and simulator:
            try:
                substance_files = export_csv_substance_fields(simulator, str(checkpoint_dir), step)
                if substance_files:
                    print(f"[CHECKPOINT] Saved {len(substance_files)} substance fields at step {step}")
            except Exception as e:
                print(f"[CHECKPOINT] Warning: Failed to save substance fields: {e}")
                # Don't fail the whole checkpoint if substances fail

        return True

    except Exception as e:
        print(f"[CHECKPOINT] Error saving CSV checkpoint: {e}")
        import traceback
        traceback.print_exc()
        return False


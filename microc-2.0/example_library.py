"""
Example Function Library for MicroC v2.0

This library demonstrates how to create custom workflow functions
that can be imported into the GUI.
"""

def custom_analysis(context, **kwargs):
    """
    Perform custom analysis on simulation data.
    
    This is an example function that shows how to:
    - Access context variables
    - Save results to the subworkflow results directory
    - Use matplotlib for visualization
    """
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Get results directory from context
    results_dir = context.get('subworkflow_results_dir')
    
    # Create some example data
    x = np.linspace(0, 10, 100)
    y = np.sin(x)
    
    # Create plot
    plt.figure(figsize=(10, 6))
    plt.plot(x, y, 'b-', linewidth=2)
    plt.title('Custom Analysis Result')
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.grid(True, alpha=0.3)
    
    # Save to results directory
    if results_dir:
        analysis_dir = results_dir / 'custom'
        analysis_dir.mkdir(parents=True, exist_ok=True)
        plt.savefig(analysis_dir / 'custom_analysis.png', dpi=150, bbox_inches='tight')
        print(f"[custom_analysis] Saved plot to {analysis_dir / 'custom_analysis.png'}")
    
    plt.close()


def data_processor(context, **kwargs):
    """
    Process and transform simulation data.
    
    Example function showing data processing workflow.
    """
    print("[data_processor] Processing data...")
    
    # Get parameters
    threshold = kwargs.get('threshold', 0.5)
    
    # Simulate some processing
    print(f"[data_processor] Using threshold: {threshold}")
    print("[data_processor] Processing complete")
    
    return {'status': 'success', 'threshold': threshold}


def export_results(context, **kwargs):
    """
    Export results to various formats.
    
    Example function showing how to export data.
    """
    import json
    from pathlib import Path
    
    results_dir = context.get('subworkflow_results_dir')
    
    # Create export data
    export_data = {
        'subworkflow': context.get('subworkflow_name'),
        'kind': context.get('subworkflow_kind'),
        'timestamp': str(context.get('timestamp', 'unknown')),
        'parameters': kwargs
    }
    
    # Save to JSON
    if results_dir:
        export_dir = results_dir / 'exports'
        export_dir.mkdir(parents=True, exist_ok=True)
        
        export_file = export_dir / 'export.json'
        with open(export_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"[export_results] Exported to {export_file}")
    
    return export_data


def initialize_custom(context, **kwargs):
    """
    Custom initialization function.
    
    This function could conflict with built-in initialization functions
    to demonstrate the conflict resolution dialog.
    """
    print("[initialize_custom] Running custom initialization...")
    
    # Set up custom context variables
    context['custom_initialized'] = True
    context['custom_config'] = kwargs
    
    print("[initialize_custom] Initialization complete")
    
    return {'initialized': True}


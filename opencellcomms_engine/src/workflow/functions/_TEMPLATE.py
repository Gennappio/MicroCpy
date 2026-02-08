"""
[Function Name] - [Brief description]

[Detailed description of what this function does and when to use it]

Example:
    This function can be used in workflows like:
    - [Use case 1]
    - [Use case 2]

Notes:
    - [Important note 1]
    - [Important note 2]
"""

from typing import Dict, Any, Optional
from src.workflow.decorators import register_function
from src.interfaces.base import ICellPopulation, IGeneNetwork  # Import interfaces as needed


@register_function(
    display_name="[Display Name for GUI]",
    description="[Description shown in GUI tooltip - be specific about what this does]",
    category="INTRACELLULAR",  # Options: INITIALIZATION, INTRACELLULAR, DIFFUSION, INTERCELLULAR, FINALIZATION, UTILITY
    parameters=[
        {
            "name": "my_param",
            "type": "INT",  # Options: INT, FLOAT, BOOL, STRING
            "description": "Description of this parameter",
            "default": 100,
            "min_value": 0,      # Optional for INT/FLOAT
            "max_value": 1000    # Optional for INT/FLOAT
        },
        {
            "name": "enable_feature",
            "type": "BOOL",
            "description": "Enable this feature",
            "default": True
        },
        {
            "name": "mode",
            "type": "STRING",
            "description": "Operating mode",
            "default": "normal",
            "options": ["normal", "fast", "accurate"]  # Optional for STRING
        }
    ],
    inputs=["context"],  # ← ALWAYS use ["context"] - this is the recommended pattern
    outputs=[],          # List any outputs this function produces (usually empty)
    cloneable=False,     # Set to True if users should be able to duplicate/customize this
    compatible_kernels=["biophysics"]  # ← REQUIRED! List which kernels this works with
)
def my_function_name(
    context: Dict[str, Any] = None,  # ← ONLY context in signature (recommended pattern)
    my_param: int = 100,              # Parameters from decorator
    enable_feature: bool = True,
    mode: str = "normal",
    **kwargs                          # Always include **kwargs for forward compatibility
) -> bool:
    """
    [Function description - more detailed than the decorator description]
    
    This function does X, Y, and Z. It expects the following items in context:
    - population: ICellPopulation instance
    - [other required context items]
    
    Args:
        context: Workflow context containing population, simulator, config, etc.
        my_param: Description of this parameter
        enable_feature: Description of this parameter
        mode: Description of this parameter
        **kwargs: Additional parameters (for forward compatibility)
        
    Returns:
        True if successful, False otherwise
    """
    # =========================================================================
    # VALIDATE CONTEXT
    # =========================================================================
    if not context:
        print("[ERROR] [my_function_name] No context provided")
        return False
    
    # =========================================================================
    # GET REQUIRED ITEMS FROM CONTEXT
    # =========================================================================
    population = context.get('population')
    if population is None:
        print("[ERROR] [my_function_name] No population in context")
        return False
    
    # Get optional items with defaults
    config = context.get('config')
    gene_networks = context.get('gene_networks', {})
    
    # =========================================================================
    # VALIDATE PARAMETERS
    # =========================================================================
    if my_param < 0:
        print(f"[ERROR] [my_function_name] Invalid my_param: {my_param}")
        return False
    
    # =========================================================================
    # FUNCTION LOGIC
    # =========================================================================
    print(f"[MY_FUNCTION] Starting with mode={mode}, my_param={my_param}")
    
    cells = population.state.cells
    num_cells = len(cells)
    
    # Example: Process each cell
    processed_count = 0
    for cell_id, cell in cells.items():
        # Do something with the cell
        # ...
        processed_count += 1
    
    print(f"[MY_FUNCTION] Processed {processed_count}/{num_cells} cells")
    
    # =========================================================================
    # UPDATE CONTEXT (if needed)
    # =========================================================================
    # Only update context if this function produces new data
    # context['my_results'] = some_results
    
    return True


# ============================================================================
# CHECKLIST BEFORE COMMITTING:
# ============================================================================
# [ ] Function name is descriptive and follows snake_case convention
# [ ] Display name is clear and user-friendly
# [ ] Description explains what the function does (not just repeating the name)
# [ ] Category is correct (INITIALIZATION, INTRACELLULAR, DIFFUSION, etc.)
# [ ] All parameters have descriptions and sensible defaults
# [ ] inputs=["context"] (recommended pattern - don't add other inputs)
# [ ] compatible_kernels is specified
# [ ] Function signature only has context + parameters (no other inputs)
# [ ] Context validation is present (check if context exists)
# [ ] Required context items are validated (check if they exist)
# [ ] Error messages include function name for easy debugging
# [ ] Function is imported in src/workflow/registry.py
# [ ] Function has been tested with a workflow JSON
# ============================================================================


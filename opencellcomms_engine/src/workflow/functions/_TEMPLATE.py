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

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext


@register_function(
    display_name="[Display Name for GUI]",
    description="[Description shown in GUI tooltip - be specific about what this does]",
    # Legacy registry metadata only; v2 execution is controlled by the graph.
    category="INTRACELLULAR",
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
    compatible_kernels=["biophysics"],  # ← REQUIRED! List which kernels this works with
    requires=["population"]  # ← Capability tokens this function needs from the kernel.
                             #    The workflow fails to load (loudly) if the kernel does not
                             #    provide all of them. Structural tokens are bare context keys
                             #    the function reads (e.g. "population", "simulator",
                             #    "gene_networks"). Reserved ontology tokens use the form
                             #    "substance:<name>", "gene:<name>", "phenotype:<name>".
)
def my_function_name(
    env: BiologicalContext,           # ← typed biological context (recommended pattern)
    my_param: int = 100,              # Parameters from decorator
    enable_feature: bool = True,
    mode: str = "normal",
    **kwargs                          # Always include **kwargs for forward compatibility
) -> bool:
    """
    [Function description - more detailed than the decorator description]

    Args:
        env: Typed biological context (cells, substances, genes, results).
            Declare what you read via `requires=[...]` above; the typed views
            fail loudly if the kernel doesn't provide it, so no None-checks needed.
        my_param: Description of this parameter
        enable_feature: Description of this parameter
        mode: Description of this parameter
        **kwargs: Additional parameters (for forward compatibility)

    Returns:
        True if successful, False otherwise
    """
    # Config is always available; cells/substances are guaranteed by `requires`.
    config = env.config

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

    num_cells = len(env.cells)

    # Example: process each cell through the typed API
    processed_count = 0
    for cell in env.cells:
        # e.g. read the local environment and mark a phenotype:
        #   if env.concentration('oxygen', cell) < my_param:
        #       cell.mark_necrotic()
        processed_count += 1

    print(f"[MY_FUNCTION] Processed {processed_count}/{num_cells} cells")

    # =========================================================================
    # STORE RESULTS (if needed)
    # =========================================================================
    # Only store if this function produces new data:
    # env.results.store('my_results', some_results)

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
# [ ] requires lists the capability tokens this function needs (or [] if none)
# [ ] Function signature is (env: BiologicalContext, ...parameters)
# [ ] Uses the typed env API (env.cells, cell.mark_*) — no manual None-checks needed
# [ ] Error messages include function name for easy debugging
# [ ] Function is imported in src/workflow/registry.py
# [ ] Function has been tested with a workflow JSON
# ============================================================================

"""
[Function Name] - [Brief description]

[Detailed description of what this function does and when to use it]

Which canvas does this belong on? (collective vs per-agent — the #1 structural choice)
    - Creation (create_subworkflow, authored in World) and collective reporting run
      ONCE: env.agent is None; use `for cell in env.cells:` /
      `env.population.populate(...)`. The example below is this collective shape.
    - Per-agent init (init_subworkflow) and per-agent step (behavior_subworkflows)
      run ONCE PER AGENT via for_each: use `agent = env.agent` (guard `is None`) and
      never loop `env.cells`.
    Getting this wrong is the classic bug in both directions: a `for cell` loop in a
    per-agent function double-iterates; an `env.agent` function on a creation canvas
    does nothing (env.agent is None).

Example:
    This function can be used in workflows like:
    - [Use case 1]
    - [Use case 2]

Notes:
    - [Important note 1]
    - [Important note 2]

Readability Contract (docs/READABILITY.md — mandatory, strictly enforced):
    - R1: every biological constant in the body is a declared parameter (prefer
      one DICT), consumed and proven with a non-default value — never hardcoded.
    - R1.6: a law/mode switch is its own node or clearly-labeled slot, announced
      on the canvas — never a free-form key inside a dict entry (scientists do
      not go deeper than the canvas).
    - R2: one source of truth — reuse a shared helper for an existing law and
      read values from their owning parameter table; never copy either.
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
    # FUNCTION LOGIC — pick the shape that matches THIS function's canvas.
    # (The role-aware GUI scaffold / occ_new-function writes the right shape for
    # you automatically; this template is only a hand-authoring reference.)
    # =========================================================================
    print(f"[MY_FUNCTION] Starting with mode={mode}, my_param={my_param}")

    # PER-AGENT (agent Step / per-agent init) — runs once per agent via for_each:
    #   agent = env.agent            # the single bound agent (None if the ask is empty)
    #   if agent is None:
    #       return True
    #   agent.set('key', agent.get('key', 0) + 1)   # act on this ONE agent
    #
    # COLLECTIVE (creation / reporting) — runs once over the whole population:
    #   for cell in env.cells:
    #       if env.concentration('oxygen', cell) < my_param:
    #           cell.mark_necrotic()
    #   # ...or create agents: env.population.populate('kind', count, trait=lambda rng: ...)

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
# [ ] Uses the typed env API in the shape the canvas needs — per-agent (env.agent) OR
#     collective (env.cells / env.population.populate); no manual None-checks needed
# [ ] Error messages include function name for easy debugging
# [ ] Function is imported in src/workflow/registry.py
# [ ] Function has been tested with a workflow JSON
# ============================================================================

"""
Test functions for Context Registry Test Project.
These functions demonstrate context key usage.
"""

from microc import register_function


@register_function(
    name="initialize_simulation",
    description="Initialize the simulation with default parameters",
    inputs=[],
    outputs=["core.population", "core.grid", "simulation.step_count"]
)
def initialize_simulation(context):
    """Initialize the simulation environment."""
    context["core.population"] = []
    context["core.grid"] = {"width": 100, "height": 100}
    context["simulation.step_count"] = 0
    print("[INIT] Simulation initialized")
    return context


@register_function(
    name="run_step",
    description="Run a single simulation step",
    inputs=["core.population", "simulation.step_count"],
    outputs=["simulation.step_count"]
)
def run_step(context):
    """Execute one simulation step."""
    step = context.get("simulation.step_count", 0)
    context["simulation.step_count"] = step + 1
    print(f"[STEP] Running step {step + 1}")
    return context


@register_function(
    name="collect_output",
    description="Collect simulation output data",
    inputs=["core.population", "simulation.step_count"],
    outputs=["output.data"]
)
def collect_output(context):
    """Collect and store output data."""
    step = context.get("simulation.step_count", 0)
    population = context.get("core.population", [])
    
    output = context.get("output.data", [])
    if output is None:
        output = []
    
    output.append({
        "step": step,
        "population_size": len(population)
    })
    
    context["output.data"] = output
    print(f"[OUTPUT] Collected data for step {step}")
    return context


@register_function(
    name="save_results",
    description="Save results to file",
    inputs=["output.data", "results_dir"],
    outputs=[]
)
def save_results(context):
    """Save output data to results directory."""
    results_dir = context.get("results_dir", "./results")
    output_data = context.get("output.data", [])
    
    print(f"[SAVE] Would save {len(output_data)} records to {results_dir}")
    return context


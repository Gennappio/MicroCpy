"""
Setup gene network configuration.

This function configures gene network parameters.
"""

from typing import Dict, Any
from pathlib import Path
from src.workflow.decorators import register_function


@register_function(
    display_name="Setup Gene Network",
    description="Configure gene network parameters (propagation steps, BND file, etc.)",
    category="INITIALIZATION",
    parameters=[
        {"name": "bnd_file", "type": "STRING", "description": "Path to BND file (relative to workflow)", "default": "gene_network.bnd"},
        {"name": "propagation_steps", "type": "INT", "description": "Number of propagation steps", "default": 500},
        {"name": "random_initialization", "type": "BOOL", "description": "Use random initialization", "default": True},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False
)
def setup_gene_network(
    context: Dict[str, Any],
    bnd_file: str = "gene_network.bnd",
    propagation_steps: int = 500,
    random_initialization: bool = True,
    **kwargs
) -> bool:
    """
    Setup gene network configuration.

    Args:
        context: Workflow context
        bnd_file: Path to BND file
        propagation_steps: Number of propagation steps
        random_initialization: Use random initialization
        **kwargs: Additional parameters

    Returns:
        True if successful
    """
    print(f"[WORKFLOW] Setting up gene network configuration")

    try:
        config = context.get('config')

        if not config:
            print("[ERROR] Config must be set up before gene network")
            return False

        # === CLEAN ARCHITECTURE: Use context['resolve_path'] if available ===
        if 'resolve_path' in context:
            resolve_path = context['resolve_path']
            bnd_path = resolve_path(bnd_file)
            if bnd_path.exists():
                print(f"   [+] Resolved BND file: {bnd_path}")
            else:
                print(f"   [!] WARNING: BND file not found: {bnd_file}")
        else:
            # Fallback to local resolution for legacy contexts
            bnd_path = Path(bnd_file)
            if not bnd_path.is_absolute() and not bnd_path.exists():
                resolved = False
                project_root = Path(__file__).parent.parent.parent.parent.parent

                # Strategy 1: Relative to workflow file directory
                workflow_file = context.get('workflow_file')
                if workflow_file:
                    workflow_dir = Path(workflow_file).parent
                    resolved_path = workflow_dir / bnd_file
                    if resolved_path.exists():
                        bnd_path = resolved_path
                        resolved = True
                        print(f"   [+] Resolved BND file (workflow-relative): {bnd_path}")

                # Strategy 2: Relative to project root
                if not resolved:
                    resolved_path = project_root / bnd_file
                    if resolved_path.exists():
                        bnd_path = resolved_path
                        resolved = True
                        print(f"   [+] Resolved BND file (project-root-relative): {bnd_path}")

                # Strategy 3: Search in tests/ directory
                if not resolved:
                    tests_dir = project_root / "tests"
                    if tests_dir.exists():
                        for found_path in tests_dir.rglob(bnd_file):
                            if found_path.is_file():
                                bnd_path = found_path
                                resolved = True
                                print(f"   [+] Resolved BND file (found in tests/): {bnd_path}")
                                break

                if not resolved:
                    print(f"   [!] WARNING: BND file not found: {bnd_file}")

        # Create gene network config object
        class GeneNetworkConfig:
            def __init__(self, bnd, prop_steps, rand_init):
                self.bnd_file = str(bnd)
                self.propagation_steps = prop_steps
                self.random_initialization = rand_init
                self.output_nodes = ["Proliferation", "Apoptosis", "Growth_Arrest", "Necrosis"]
                self.nodes = {}

        config.gene_network = GeneNetworkConfig(bnd_path, propagation_steps, random_initialization)

        print(f"   [+] BND file: {bnd_path}")
        print(f"   [+] Propagation steps: {propagation_steps}")
        print(f"   [+] Random initialization: {random_initialization}")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to setup gene network: {e}")
        import traceback
        traceback.print_exc()
        return False


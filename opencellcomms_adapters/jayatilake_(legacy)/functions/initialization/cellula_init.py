"""
cellula_init — auto-generated behavior scaffold.

Edit the function bodies below to implement the behavior logic.
"""

from src.workflow.decorators import register_function
from src.biology.context import BiologicalContext



@register_function(
    display_name="Mettiqua",
    description="TODO: describe what mettiqua does",
    category="INITIALIZATION",
    parameters=[
        {"name": "nome", "type": "FLOAT", "description": "TODO", "default": 0},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def mettiqua(
    env: BiologicalContext = None,
    nome: float = 0,
    **kwargs
) -> bool:
    print("CIAOOOOOOOOOOOO")
    """TODO: implement mettiqua."""
    if env is None:
        print("[ERROR] [mettiqua] No context provided")
        return False
    # TODO: implement behavior
    return True


"""
prima_func — auto-generated behavior scaffold.

Edit the function bodies below to implement the behavior logic.
"""

from typing import Dict, Any
from src.workflow.decorators import register_function



@register_function(
    display_name="Func1",
    description="TODO: describe what func1 does",
    category="INTRACELLULAR",
    parameters=[
        {"name": "parme", "type": "FLOAT", "description": "TODO", "default": 3},
    ],
    inputs=["context"],
    outputs=[],
    cloneable=False,
)
def func1(
    context: Dict[str, Any] = None,
    parme: float = 3,
    **kwargs
) -> bool:
    """TODO: implement func1."""
    if not context:
        print("[ERROR] [func1] No context provided")
        return False
    # TODO: implement behavior
    return True


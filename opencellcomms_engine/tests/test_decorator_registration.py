"""Decorator-based function registration.

Verifies the core @register_function mechanism: a decorated function lands in the
decorator registry with correct, signature-extracted metadata; the default
registry is populated; and manual + decorator registries merge. Self-contained —
no external fixtures (the old script-style version depended on the removed
tests/jayatilake_experiment data).
"""

from src.workflow.decorators import (
    register_function,
    get_decorator_registry,
    merge_registries,
)
from src.workflow.registry import FunctionRegistry, get_default_registry


def test_register_function_adds_to_decorator_registry_with_metadata():
    @register_function(
        display_name="Sample Threshold",
        description="a sample function for the registration test",
        category="INTRACELLULAR",
        parameters=[{"name": "threshold", "type": "FLOAT", "default": 0.5}],
        inputs=["context"],
    )
    def _sample_registration_fn(context, threshold: float = 0.5, **kwargs):
        return threshold

    meta = get_decorator_registry().get("_sample_registration_fn")
    assert meta is not None
    assert meta.display_name == "Sample Threshold"
    # the declared parameter became an editable parameter definition (a GUI socket)
    assert any(p.name == "threshold" for p in meta.parameters)


def test_default_registry_is_populated():
    # get_default_registry imports the standard function modules to trigger
    # registration, so it should expose the engine's built-in functions.
    assert len(get_default_registry().list_all()) > 0


def test_merge_registries_unions_decorator_functions():
    decorator = get_decorator_registry()
    merged = merge_registries(FunctionRegistry(), decorator)
    assert len(merged.list_all()) >= len(decorator.list_all())

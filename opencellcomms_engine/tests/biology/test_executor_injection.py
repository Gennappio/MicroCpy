"""
End-to-end check: verify the executor actually injects BiologicalContext into
functions that opt in via `env: BiologicalContext`, and still passes raw
`context: Dict` to functions that don't.
"""

import os
import sys
from typing import Dict, Any

import pytest

_THIS_DIR = os.path.dirname(__file__)
_ENGINE_ROOT = os.path.abspath(os.path.join(_THIS_DIR, '..', '..'))
if _ENGINE_ROOT not in sys.path:
    sys.path.insert(0, _ENGINE_ROOT)

from src.biology.context import BiologicalContext
from src.workflow.executor import _wants_typed_env


def fn_with_env(env: BiologicalContext, factor: float = 1.0):
    return ('env', type(env).__name__, factor)


def fn_with_context(context: Dict[str, Any], factor: float = 1.0):
    return ('ctx', type(context).__name__, factor)


def fn_with_quoted_env(env: 'BiologicalContext', factor: float = 1.0):
    return ('env-quoted', type(env).__name__, factor)


def fn_no_first_arg(factor: float = 1.0):
    return ('none', factor)


def fn_env_no_annotation(env, factor: float = 1.0):
    return ('env-noannot', factor)


def test_wants_typed_env_detects_class_annotation():
    assert _wants_typed_env(fn_with_env) is True


def test_wants_typed_env_detects_quoted_annotation():
    assert _wants_typed_env(fn_with_quoted_env) is True


def test_wants_typed_env_rejects_legacy_context():
    assert _wants_typed_env(fn_with_context) is False


def test_wants_typed_env_rejects_no_args():
    assert _wants_typed_env(fn_no_first_arg) is False


def test_wants_typed_env_rejects_unannotated_env():
    """`env` parameter without BiologicalContext annotation does not opt in."""
    assert _wants_typed_env(fn_env_no_annotation) is False


def test_wants_typed_env_caches_result():
    """Calling twice returns same result; cache hit doesn't crash."""
    a = _wants_typed_env(fn_with_env)
    b = _wants_typed_env(fn_with_env)
    assert a == b is True


def test_migrated_mark_necrotic_signature_opts_in():
    """The actual migrated MicroC function opts into the typed env."""
    adapters_root = os.path.abspath(os.path.join(_ENGINE_ROOT, '..'))
    if adapters_root not in sys.path:
        sys.path.insert(0, adapters_root)
    from opencellcomms_adapters.MicroC.functions.fate.mark_necrotic_cells import (
        mark_necrotic_cells,
    )
    assert _wants_typed_env(mark_necrotic_cells) is True


def test_legacy_function_signature_does_not_opt_in():
    """A non-migrated style function (context: Dict) is correctly detected as legacy."""
    def legacy(context: Dict[str, Any], **kwargs):
        return True
    assert _wants_typed_env(legacy) is False

"""Tests for select_project_template workflow node (Phase 4.5)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import pytest

from opencellcomms_adapters.PhysiBoSS.functions.select_project_template import select_project_template


PHYSIBOSS_ROOT = os.environ.get("PHYSIBOSS_ROOT")
has_physiboss = pytest.mark.skipif(
    not PHYSIBOSS_ROOT or not (Path(PHYSIBOSS_ROOT) / "core").is_dir(),
    reason="PHYSIBOSS_ROOT not set or invalid",
)


def test_no_context_returns_false():
    assert select_project_template(context=None, project_name="x") is False


def test_empty_project_name_is_noop():
    ctx: Dict[str, Any] = {}
    ok = select_project_template(context=ctx, project_name="")
    assert ok is True
    assert "physicell_spec" not in ctx or "custom_modules_source" not in ctx.get("physicell_spec", {})


def test_blank_project_name_is_noop():
    ctx: Dict[str, Any] = {}
    ok = select_project_template(context=ctx, project_name="   ")
    assert ok is True


@has_physiboss
def test_known_project_writes_source_entry():
    ctx: Dict[str, Any] = {}
    ok = select_project_template(context=ctx, project_name="rules_sample")
    assert ok is True
    src = ctx["physicell_spec"]["custom_modules_source"]
    assert src["type"] == "sample_project"
    assert src["project_name"] == "rules_sample"
    assert Path(src["source_dir"]).is_dir()


@has_physiboss
def test_unknown_project_returns_false(capsys):
    ctx: Dict[str, Any] = {}
    ok = select_project_template(context=ctx, project_name="nonexistent_project_xyz")
    assert ok is False
    out = capsys.readouterr().out
    assert "nonexistent_project_xyz" in out
    assert "Available" in out


@has_physiboss
def test_initialises_physicell_spec_if_missing():
    ctx: Dict[str, Any] = {}
    ok = select_project_template(context=ctx, project_name="rules_sample")
    assert ok is True
    assert "physicell_spec" in ctx


@has_physiboss
def test_preserves_existing_spec_keys():
    ctx: Dict[str, Any] = {"physicell_spec": {"substrates": [{"name": "oxygen"}]}}
    ok = select_project_template(context=ctx, project_name="rules_sample")
    assert ok is True
    assert ctx["physicell_spec"]["substrates"][0]["name"] == "oxygen"
    assert "custom_modules_source" in ctx["physicell_spec"]

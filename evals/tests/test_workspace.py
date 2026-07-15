"""workspace.py is the contamination control — its strip/rewrite/condition logic is
correctness-critical. Tested on a synthetic mini-repo so it's fast and hermetic; a
single real build against the live tree is a slow test."""
import json

import pytest

from evals.harness import workspace as W


def _mini_repo(root):
    """A tiny repo with the shape build_workspace depends on: three plugins, a
    CLAUDE.md + occ command that name the canonical workflows, a validator stub."""
    def w(rel, text):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    w("CLAUDE.md",
      "Copy examples only from canonical workflows —\n"
      "`MicroC/workflows/microc.json`, `TCELL_CORRAL/workflows/tcell_corral.json`,\n"
      "`SUGARSCAPE/workflows/sugarscape.json`. Never copy skip-marked.\n")
    w(".claude/commands/occ_new-model.md",
      "Read the nearest plugin's canonical workflow — sugarscape.json / microc.json.\n")
    w(".claude/commands/occ_create-workflow.md", "Assemble a workflow.\n")
    w("opencellcomms_engine/scripts/validate_workflow.py", "# validator stub\n")

    # target plugin: SUGARSCAPE
    bench = {
        "version": "2.0", "name": "Sugarscape",
        "metadata": {"gui": {"agent_kinds": [{"name": "forager",
                     "create_subworkflow": "forager_create", "behavior_subworkflows": ["forager_step"]}]}},
        "subworkflows": {
            "main": {}, "forager_create": {"functions": [{"function_name": "place_foragers"}]},
            "forager_step": {"functions": [{"function_name": "move_to_best_sugar"},
                                           {"function_name": "eat_sugar"}]},
        },
    }
    w("opencellcomms_adapters/SUGARSCAPE/MODEL.md", "# Sugarscape model\nBiology...\n")
    w("opencellcomms_adapters/SUGARSCAPE/plugin.toml", "[plugin]\nname='SUGARSCAPE'\n")
    w("opencellcomms_adapters/SUGARSCAPE/register.py", "import ...\n")
    w("opencellcomms_adapters/SUGARSCAPE/functions/forager/place_foragers.py", "def place_foragers(env): ...\n")
    w("opencellcomms_adapters/SUGARSCAPE/data/params.csv", "a,b\n1,2\n")
    w("opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json", json.dumps(bench))
    # other plugins (examples)
    w("opencellcomms_adapters/MicroC/workflows/microc.json", json.dumps({"version": "2.0", "subworkflows": {}}))
    w("opencellcomms_adapters/TCELL_CORRAL/workflows/tcell_corral.json", json.dumps({"version": "2.0", "subworkflows": {}}))
    return root


def _case():
    return {
        "name": "sugarscape",
        "plugin": "opencellcomms_adapters/SUGARSCAPE",
        "benchmark_workflow": "opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json",
        "quarantine": {"strip": ["functions", "workflows", "register.py"],
                       "keep": ["MODEL.md", "plugin.toml", "data"]},
        "reference_rewrite": {"allowed_examples": ["MicroC", "TCELL_CORRAL"]},
    }


FULL = {"id": "full", "scaffold": {"claude_md": True, "occ_protocols": True, "validator": True, "canonical_examples": True}}
NAKED = {"id": "naked", "scaffold": {"claude_md": False, "occ_protocols": False, "validator": False, "canonical_examples": False}}
NO_VAL = {"id": "no_validator", "scaffold": {"claude_md": True, "occ_protocols": True, "validator": False, "canonical_examples": True}}


def test_strip_keeps_model_and_inputs(tmp_path):
    src = _mini_repo(tmp_path / "src")
    ws = W.build_workspace(_case(), FULL, tmp_path / "ws", source_root=src)
    plug = ws.root / "opencellcomms_adapters/SUGARSCAPE"
    assert (plug / "MODEL.md").exists()          # kept
    assert (plug / "plugin.toml").exists()       # kept
    assert (plug / "data" / "params.csv").exists()  # inputs kept
    assert not (plug / "functions").exists()     # stripped
    assert not (plug / "register.py").exists()   # stripped
    assert not (plug / "workflows").exists()     # stripped


def test_quarantine_manifest_lists_original_paths_and_identifiers(tmp_path):
    src = _mini_repo(tmp_path / "src")
    ws = W.build_workspace(_case(), FULL, tmp_path / "ws", source_root=src)
    assert any("sugarscape.json" in p for p in ws.quarantined_paths)
    assert any("functions" in p for p in ws.quarantined_paths)
    # distinctive function names become leak identifiers; generic ones are excluded
    assert "move_to_best_sugar" in ws.identifiers
    assert "place_foragers" in ws.identifiers


def test_reference_rewrite_drops_only_target(tmp_path):
    src = _mini_repo(tmp_path / "src")
    ws = W.build_workspace(_case(), FULL, tmp_path / "ws", source_root=src)
    claude = (ws.root / "CLAUDE.md").read_text()
    assert "sugarscape.json" not in claude      # target example removed
    assert "microc.json" in claude              # other models still primed
    occ = (ws.root / ".claude/commands/occ_new-model.md").read_text()
    assert "sugarscape.json" not in occ


def test_full_keeps_only_allowed_examples(tmp_path):
    src = _mini_repo(tmp_path / "src")
    ws = W.build_workspace(_case(), FULL, tmp_path / "ws", source_root=src)
    adapters = ws.root / "opencellcomms_adapters"
    assert (adapters / "MicroC/workflows/microc.json").exists()          # allowed example kept
    assert (adapters / "TCELL_CORRAL/workflows/tcell_corral.json").exists()
    assert not (adapters / "SUGARSCAPE/workflows/sugarscape.json").exists()  # target stripped


def test_naked_removes_all_scaffold(tmp_path):
    src = _mini_repo(tmp_path / "src")
    ws = W.build_workspace(_case(), NAKED, tmp_path / "ws", source_root=src)
    assert not (ws.root / "CLAUDE.md").exists()
    assert not (ws.root / ".claude/commands/occ_new-model.md").exists()
    assert not (ws.root / "opencellcomms_engine/scripts/validate_workflow.py").exists()
    # no example workflows at all
    assert not list((ws.root / "opencellcomms_adapters").glob("*/workflows/*.json"))


def test_no_validator_removes_validator_only(tmp_path):
    src = _mini_repo(tmp_path / "src")
    ws = W.build_workspace(_case(), NO_VAL, tmp_path / "ws", source_root=src)
    assert (ws.root / "CLAUDE.md").exists()      # kept
    assert not (ws.root / "opencellcomms_engine/scripts/validate_workflow.py").exists()  # removed
    assert (ws.root / "opencellcomms_adapters/MicroC/workflows/microc.json").exists()  # examples kept


def test_manifest_written(tmp_path):
    src = _mini_repo(tmp_path / "src")
    ws = W.build_workspace(_case(), FULL, tmp_path / "ws", source_root=src)
    manifest = json.loads((ws.root / ".eval_manifest.json").read_text())
    assert manifest["case"] == "sugarscape" and manifest["condition"] == "full"


@pytest.mark.slow
def test_real_repo_build(tmp_path):
    """One real build against the live tree: it copies, strips, and rewrites without
    error, and the target's code is genuinely gone."""
    from evals.harness import config
    ws = W.build_workspace(config.load_case("sugarscape"),
                           config.load_condition("full"), tmp_path / "ws")
    assert not (ws.root / "opencellcomms_adapters/SUGARSCAPE/functions").exists()  # stripped
    assert (ws.root / "opencellcomms_engine").exists()   # engine copied (needed to run/validate)
    assert not (ws.root / ".git").exists()               # history not recoverable
    assert any("sugarscape.json" in p for p in ws.quarantined_paths)

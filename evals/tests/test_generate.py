"""Generation plumbing (workspace + MODEL.md placement + prompt/command assembly +
candidate location) is unit-tested here; the actual claude -p spawn is the smoke
run and is not exercised. A dry-run must fully prepare a run without spawning."""
import json
from pathlib import Path

from evals.harness import generate as G
from evals.harness.biologist import Biologist

import pytest

DRAFTS = Path(__file__).resolve().parents[1] / "model_drafts"
SUGAR_DRAFT = DRAFTS / "SUGARSCAPE.MODEL.md"


@pytest.mark.parametrize("draft", sorted(DRAFTS.glob("*.MODEL.md")), ids=lambda p: p.stem)
def test_biology_brief_keeps_biology_drops_structure(draft):
    """Every staged draft must yield a non-empty Tier-2 brief that keeps the biology
    and drops the structural slots — regardless of hyphenation quirks in its header."""
    brief = G.biology_brief(draft.read_text(encoding="utf-8"))
    assert brief, f"{draft.name}: empty brief (divider/marker parse bug)"
    assert "## Provenance" in brief
    assert "## Biology" in brief
    assert "## Observables" in brief
    # Tier-1-only structural slots must NOT leak into the Tier-2 brief
    assert "## World" not in brief
    assert "## Agents" not in brief
    assert "## Scheduler" not in brief


def test_assemble_prompt_protocol_vs_freeform():
    case = {"plugin": "opencellcomms_adapters/SUGARSCAPE"}
    proto = G.assemble_prompt(case, {"entry": "occ_new-model"}, "spec2code", "…/MODEL.md")
    free = G.assemble_prompt(case, {"entry": "freeform"}, "spec2code", "…/MODEL.md")
    assert "/occ_new-model" in proto and "biologist" in proto.lower()
    assert "/occ_new-model" not in free


def test_assemble_prompt_tier_framing():
    case = {"plugin": "opencellcomms_adapters/SUGARSCAPE"}
    t1 = G.assemble_prompt(case, {"entry": "freeform"}, "spec2code", "m.md")
    t2 = G.assemble_prompt(case, {"entry": "freeform"}, "bio2code", "m.md")
    assert "derive" in t2.lower()          # Tier 2 must tell the agent to derive structure
    assert "derive" not in t1.lower()


def test_build_command_flags():
    cmd = G.build_command("do it", Path("/ws"), "claude-fable-5", "high")
    assert "claude" == cmd[0] and "-p" in cmd
    assert "stream-json" in cmd and "--verbose" in cmd
    assert "claude-fable-5" in cmd
    assert "--dangerously-skip-permissions" in cmd


def test_locate_candidate_workflow(tmp_path):
    from evals.harness import workspace as WS
    ws = WS.Workspace(root=tmp_path, case="c", condition="full")
    wfdir = tmp_path / "opencellcomms_adapters/SUGARSCAPE/workflows"
    wfdir.mkdir(parents=True)
    (wfdir / "sugarscape.json").write_text("{}")
    got = G.locate_candidate_workflow(ws, {"plugin": "opencellcomms_adapters/SUGARSCAPE"})
    assert got and got.endswith("sugarscape.json")


def test_dry_run_prepares_without_spawning(tmp_path):
    """The whole pipeline must assemble — quarantine, MODEL.md placed, prompt + command
    ready — without spawning the agent."""
    res = G.run("sugarscape", "full", "spec2code", tmp_path / "out", dry_run=True)
    assert res.spawned is False
    assert res.transcript is None
    ws_root = Path(res.workspace)
    # MODEL.md placed into the quarantined plugin, benchmark code stripped
    assert (ws_root / "opencellcomms_adapters/SUGARSCAPE/MODEL.md").exists()
    assert not (ws_root / "opencellcomms_adapters/SUGARSCAPE/functions").exists()
    # command + contamination manifest ready
    assert res.command[0] == "claude"
    assert res.quarantined_paths and res.identifiers


def test_dry_run_tier2_places_only_brief(tmp_path):
    res = G.run("sugarscape", "full", "bio2code", tmp_path / "out", dry_run=True)
    placed = (Path(res.workspace) / "opencellcomms_adapters/SUGARSCAPE/MODEL.md").read_text()
    assert "## Biology" in placed
    assert "## Scheduler" not in placed   # brief only


# --- biologist ---
def test_biologist_system_prompt_has_role_and_key():
    bio = Biologist(answer_key_md="# Secret model\nforagers eat sugar")
    sp = bio.system_prompt()
    assert "biologist" in sp.lower()
    assert "Secret model" in sp           # the key is embedded
    assert "NEVER paste" in sp            # and marked do-not-leak


def test_biologist_counts_preview_rounds():
    bio = Biologist(answer_key_md="x")
    bio.respond("here are my questions", gate="questions", dry_run=True)
    assert bio.rounds == 0                 # question turns are not correction rounds
    bio.respond("here is the structure", gate="preview", dry_run=True)
    bio.respond("revised structure", gate="preview", dry_run=True)
    assert bio.rounds == 2                 # each preview round-trip counts


def test_biologist_from_case_loads_draft():
    from evals.harness import config
    bio = Biologist.from_case(config.load_case("sugarscape"))
    assert "forager" in bio.answer_key_md.lower()  # loaded the staged draft

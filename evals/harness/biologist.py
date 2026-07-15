"""The simulated biologist — plays the human at /occ_new-model's two gates.

It holds an *answer key* (the ground-truth MODEL.md) and, prompted by
``prompts/biologist.md``, answers the coding agent's ``❓ NEEDS:`` questions and
approves-or-faults the previewed structure — in biology terms only, never handing
over the architecture. Each time it sends the agent back is one correction round,
the paper's headline metric.

The biologist is itself a Claude session (``claude -p``), kept separate from the
coding agent so it cannot see the agent's tools or workspace — only what the agent
says to it. This module assembles its system prompt + key and calls it; the
prompt-assembly is pure and unit-tested, the model call is a thin subprocess.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from evals.harness import _engine as E

_BIOLOGIST_PROMPT = E.REPO_ROOT / "evals" / "prompts" / "biologist.md"


@dataclass
class Biologist:
    answer_key_md: str            # the ground-truth MODEL.md (full)
    model: str = "claude-fable-5"
    rounds: int = 0               # correction rounds counted

    def system_prompt(self) -> str:
        """The biologist role + the answer key, assembled into one system prompt."""
        role = _BIOLOGIST_PROMPT.read_text(encoding="utf-8")
        return (
            f"{role}\n\n"
            f"---\n\n"
            f"## Your answer key (the ground-truth model — NEVER paste or quote this)\n\n"
            f"{self.answer_key_md}\n"
        )

    def respond(self, agent_message: str, gate: str, dry_run: bool = False) -> str:
        """Answer the agent at a gate. ``gate`` is 'questions' or 'preview'.

        Returns the biologist's reply. In ``dry_run`` mode returns a placeholder and
        does not call the model (for testing the loop plumbing)."""
        if gate == "preview":
            self.rounds += 1  # a preview turn is where a correction round is spent
        if dry_run:
            return f"[dry-run biologist reply to {gate}]"
        return _call_claude(self.system_prompt(), agent_message, self.model)

    @classmethod
    def from_case(cls, case: dict, model: str = "claude-fable-5") -> "Biologist":
        key = Path(E.REPO_ROOT / case["model_md"])
        # fall back to the staged draft if the plugin MODEL.md isn't placed yet
        if not key.exists():
            draft = E.REPO_ROOT / "evals" / "model_drafts" / f"{case['name'].upper()}.MODEL.md"
            key = draft if draft.exists() else key
        return cls(answer_key_md=key.read_text(encoding="utf-8") if key.exists() else "", model=model)


def _call_claude(system_prompt: str, user_message: str, model: str) -> str:
    """One-shot Claude call for the biologist's reply (no tools, text output)."""
    proc = subprocess.run(
        ["claude", "-p", user_message,
         "--model", model,
         "--append-system-prompt", system_prompt,
         "--output-format", "text"],
        capture_output=True, text=True, timeout=300,
    )
    return proc.stdout.strip()

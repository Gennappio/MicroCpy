#!/usr/bin/env python3
"""
In-GUI Claude coding agent for OpenCellComms.

Builds a grounded prompt from the project's biological "context API" and calls the
Anthropic API to (re)generate a single workflow function from a natural-language
description typed at a node. The API key lives server-side in a gitignored `.env`
file next to this module and is never returned to the browser.

The model returns the COMPLETE updated source file so it can be saved as a drop-in
replacement via the existing /api/function/save endpoint (which syntax-checks and
backs up before writing).
"""

import os
import re
from pathlib import Path

SERVER_DIR = Path(__file__).parent
ENV_PATH = SERVER_DIR / ".env"

KEY_VAR = "OPENCELLCOMMS_ANTHROPIC_KEY"
MODEL_VAR = "OPENCELLCOMMS_AGENT_MODEL"
DEFAULT_MODEL = "claude-sonnet-4-6"


class AgentNotConfigured(Exception):
    """Raised when no Anthropic API key has been configured yet."""


# ---------------------------------------------------------------------------
# .env read/write (tiny manual reader — no extra dependency)
# ---------------------------------------------------------------------------

def _read_env_file():
    """Parse the .env file into a dict. Returns {} if it does not exist."""
    values = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip()
    return values


def _write_env_file(values):
    """Write the dict back to .env, restricting permissions to the owner."""
    content = "\n".join(f"{k}={v}" for k, v in values.items()) + "\n"
    ENV_PATH.write_text(content, encoding="utf-8")
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass


def set_config(api_key=None, model=None):
    """Persist the API key and/or model to .env, preserving other values."""
    values = _read_env_file()
    if api_key:
        values[KEY_VAR] = api_key
    if model:
        values[MODEL_VAR] = model
    _write_env_file(values)


def get_config():
    """Return a safe, frontend-facing view of the config (never the raw key)."""
    values = _read_env_file()
    key = values.get(KEY_VAR, "")
    model = values.get(MODEL_VAR, DEFAULT_MODEL)
    if len(key) > 12:
        masked = f"{key[:6]}…{key[-4:]}"
    elif key:
        masked = "set"
    else:
        masked = ""
    return {"configured": bool(key), "model": model, "key_masked": masked}


def get_api_key():
    """Return the configured key from .env, falling back to the process env."""
    return _read_env_file().get(KEY_VAR, "") or os.environ.get(KEY_VAR, "")


# ---------------------------------------------------------------------------
# Grounding / prompt construction
# ---------------------------------------------------------------------------

# The "context API" a function author can rely on, distilled from CLAUDE.md so the
# model writes code that matches this project's conventions rather than generic Python.
_GROUNDING = """
You are a coding assistant embedded in OpenCellComms, a multi-scale agent-based
cellular simulation platform. You help biologists turn a plain-English rule into a
single registered Python workflow function. Generated code must be SIMPLE and
READABLE — a scientist must be able to read it back and trust the mechanism.

Every function receives a single `context` dict. The keys you may use:
- context['population'].cells            -> iterable of cells; cell.id, cell.position, cell.state.phenotype
- cell.position[0], cell.position[1]     -> x, y (add [2] for z in 3D)
- context['simulator'].get_substance_concentration('oxygen', x, y) -> float
- context['gene_networks'].get(cell.id)  -> the cell's BooleanNetwork (may be None)
    network.nodes['GeneName'].current_state  -> bool (read or set)
- context['current_step']                -> int
- context['dt']                          -> float (hours)
- context['results']['key'] = value      -> persist results across steps
- context['config'], context['associations']

Phenotypes (set cell.state.phenotype): 'proliferating', 'apoptotic', 'necrotic',
'growth_arrested'.

IMPORTANT conventions:
- Gene networks live in context['gene_networks'], NOT in cell.state. cell.state only
  holds gene_states: Dict[str, bool].
- Always guard context access: if not context: return False; check population exists.
- The function MUST keep the @register_function decorator and the SAME function name
  and category as the current file. Use inputs=["context"].
- Keep error messages prefixed with the function name. Print short progress lines.

Decorator shape:

    from typing import Dict, Any
    from src.workflow.decorators import register_function

    @register_function(
        display_name="...",
        description="...",
        category="INTRACELLULAR",   # one of INITIALIZATION, INTRACELLULAR, DIFFUSION, INTERCELLULAR, FINALIZATION, UTILITY
        parameters=[ { "name": "...", "type": "FLOAT", "description": "...", "default": 0.1 } ],
        inputs=["context"],
        outputs=[],
        compatible_kernels=["biophysics"],
    )
    def my_function(context: Dict[str, Any] = None, **kwargs) -> bool:
        ...
""".strip()

_OUTPUT_CONTRACT = """
RESPONSE FORMAT (strict):
1. First, 2-4 plain sentences explaining in biological terms what the function does.
2. Then a SINGLE fenced ```python code block containing the COMPLETE updated source
   FILE — all imports, the @register_function decorator, and the function body. It
   must be a drop-in replacement for the current file (do not omit anything). Do not
   include any prose after the code block.
""".strip()


def build_system_prompt(category, current_source):
    parts = [_GROUNDING]
    if category:
        parts.append(f"The node's function category is: {category.upper()}.")
    parts.append(_OUTPUT_CONTRACT)
    return "\n\n".join(parts)


def build_user_message(prompt, function_name, category, current_source):
    msg = [f"Request: {prompt}"]
    if function_name:
        msg.append(f"\nKeep the function name `{function_name}` and its category.")
    if current_source and current_source.strip():
        msg.append(
            "\nHere is the CURRENT content of the file. Modify it to satisfy the "
            "request and return the complete updated file:\n\n"
            f"```python\n{current_source}\n```"
        )
    else:
        msg.append(
            "\nThe file is new/empty. Generate a complete file from the template "
            "conventions above."
        )
    return "\n".join(msg)


_CODE_BLOCK_RE = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)


def _split_code_and_explanation(text):
    """Split the model reply into (code, explanation)."""
    match = _CODE_BLOCK_RE.search(text)
    if not match:
        # No fenced block — treat the whole reply as code as a last resort.
        return text.strip(), ""
    code = match.group(1).strip()
    explanation = text[: match.start()].strip()
    return code, explanation


# ---------------------------------------------------------------------------
# Claude call
# ---------------------------------------------------------------------------

def generate_function(prompt, function_name="", category="", current_source="", model=None):
    """Generate the complete updated source file for a node's function.

    Returns {"code": <full file>, "explanation": <prose>}.
    Raises AgentNotConfigured if no key is set.
    """
    api_key = get_api_key()
    if not api_key:
        raise AgentNotConfigured(
            "No Anthropic API key configured. Open Settings and add your key."
        )

    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "The 'anthropic' package is not installed. Run: pip install anthropic"
        ) from e

    chosen_model = model or _read_env_file().get(MODEL_VAR, DEFAULT_MODEL)
    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=chosen_model,
        max_tokens=4000,
        system=build_system_prompt(category, current_source),
        messages=[
            {"role": "user", "content": build_user_message(prompt, function_name, category, current_source)}
        ],
    )

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    code, explanation = _split_code_and_explanation(text)
    return {"code": code, "explanation": explanation, "model": chosen_model}

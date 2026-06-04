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

ANTHROPIC_KEY_VAR = "OPENCELLCOMMS_ANTHROPIC_KEY"
OPENROUTER_KEY_VAR = "OPENCELLCOMMS_OPENROUTER_KEY"
PROVIDER_VAR = "OPENCELLCOMMS_AGENT_PROVIDER"
MODEL_VAR = "OPENCELLCOMMS_AGENT_MODEL"

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openrouter": "anthropic/claude-3.5-sonnet",
}
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


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


def set_config(provider=None, model=None, anthropic_key=None, openrouter_key=None):
    """Persist provider/model/keys to .env, preserving other values.

    Keys are stored per-provider so the user can switch providers without
    re-entering credentials.
    """
    values = _read_env_file()
    if provider:
        values[PROVIDER_VAR] = provider
    if model:
        values[MODEL_VAR] = model
    if anthropic_key:
        values[ANTHROPIC_KEY_VAR] = anthropic_key
    if openrouter_key:
        values[OPENROUTER_KEY_VAR] = openrouter_key
    _write_env_file(values)


def _mask(key):
    if len(key) > 12:
        return f"{key[:6]}…{key[-4:]}"
    return "set" if key else ""


def get_config():
    """Return a safe, frontend-facing view of the config (never the raw keys)."""
    values = _read_env_file()
    provider = values.get(PROVIDER_VAR, DEFAULT_PROVIDER)
    model = values.get(MODEL_VAR) or DEFAULT_MODELS.get(provider, "")
    anthropic_key = values.get(ANTHROPIC_KEY_VAR, "")
    openrouter_key = values.get(OPENROUTER_KEY_VAR, "")
    current_key = anthropic_key if provider == "anthropic" else openrouter_key
    return {
        "provider": provider,
        "model": model,
        "anthropic_configured": bool(anthropic_key),
        "openrouter_configured": bool(openrouter_key),
        "configured": bool(current_key),
        "key_masked": _mask(current_key),
    }


def get_api_key(provider):
    """Return the configured key for a provider, falling back to the process env."""
    var = ANTHROPIC_KEY_VAR if provider == "anthropic" else OPENROUTER_KEY_VAR
    return _read_env_file().get(var, "") or os.environ.get(var, "")


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

def _call_anthropic(api_key, model, system, user):
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError(
            "The 'anthropic' package is not installed. Run: pip install anthropic"
        ) from e
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )


def _call_openrouter(api_key, model, system, user):
    """Call OpenRouter's OpenAI-compatible chat endpoint (stdlib HTTP, no extra dep)."""
    import json
    import urllib.request
    import urllib.error

    payload = {
        "model": model,
        "max_tokens": 4000,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            # Optional attribution headers recommended by OpenRouter.
            "HTTP-Referer": "https://github.com/Gennappio/MicroCpy",
            "X-Title": "OpenCellComms",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")
        raise RuntimeError(f"OpenRouter API error {e.code}: {detail[:300]}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Could not reach OpenRouter: {e.reason}")
    return data["choices"][0]["message"]["content"]


def generate_function(prompt, function_name="", category="", current_source="",
                      model=None, provider=None):
    """Generate the complete updated source file for a node's function.

    Routes to the configured provider (Anthropic direct, or OpenRouter for any
    model). Returns {"code": <full file>, "explanation": <prose>, "model", "provider"}.
    Raises AgentNotConfigured if no key is set for the active provider.
    """
    values = _read_env_file()
    provider = provider or values.get(PROVIDER_VAR, DEFAULT_PROVIDER)
    chosen_model = model or values.get(MODEL_VAR) or DEFAULT_MODELS.get(provider, "")

    api_key = get_api_key(provider)
    if not api_key:
        label = "OpenRouter" if provider == "openrouter" else "Anthropic"
        raise AgentNotConfigured(
            f"No {label} API key configured. Open Settings and add your key."
        )
    if not chosen_model:
        raise AgentNotConfigured("No model selected. Open Settings and choose a model.")

    system = build_system_prompt(category, current_source)
    user = build_user_message(prompt, function_name, category, current_source)

    if provider == "openrouter":
        text = _call_openrouter(api_key, chosen_model, system, user)
    else:
        text = _call_anthropic(api_key, chosen_model, system, user)

    code, explanation = _split_code_and_explanation(text)
    return {"code": code, "explanation": explanation, "model": chosen_model, "provider": provider}

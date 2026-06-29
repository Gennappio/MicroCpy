# /occ_create-plugin — Scaffold a new OpenCellComms plugin (adapter)

You are helping a biologist start a new **plugin** — a self-contained package of
simulation functions, behaviors, and workflows they can share, cite, run, and
fork. On disk a plugin is an **adapter** under `opencellcomms_adapters/`. Your job
is to create the package skeleton so the engine auto-discovers it on the next
restart. See `docs/PLUGINS.md` for the full model.

This command creates an **empty, import-ready package**. It does not write any
biological functions — that is `/occ_new-function`. It does not write a workflow —
that is `/occ_create-workflow`.

## Step 1 — Ask questions (ask all at once in a single message)

1. **What should the plugin be called?**
   This becomes the folder name and the manifest `name`. It must be a valid
   Python identifier: letters, digits, underscores, not starting with a digit
   (e.g. `Sugarscape`, `MicroC`, `tumor_hypoxia`). Names with other characters
   (spaces, parentheses, hyphens) are **skipped by discovery** — refuse them and
   ask for a clean name.

2. **One-line description?** Shown in the GUI plugin picker.

3. **Author?** Maintainer name (may be blank).

4. **Which kernels does it target?** Default `["*"]` (any). Use `["biophysics"]`
   if the functions are specific to the biophysics kernel.

5. **What model roles will it contain?** This decides the `functions/<role>/`
   subfolders to pre-create. Roles describe the *model object*, not an engine
   stage — e.g. an agent kind (`forager`, `tumor_cell`), a resource (`sugar`,
   `oxygen`), or a process bucket (`reporting`). If unsure, create none now;
   `/occ_new-function` will create role folders on demand.

6. **Does it need any extra Python libraries?** Packages beyond what the engine
   already ships (e.g. a special solver, a file-format reader). List them as pip
   requirement strings, or say *none*. These become the plugin's
   `requirements.txt` (see Step 3).

## Step 2 — Validate the name and check for collisions

- Confirm the name is a valid identifier (Step 1 rule). If not, stop and ask.
- Check `opencellcomms_adapters/<name>/` does not already exist. If it does, stop
  and ask whether to pick a different name (do **not** overwrite an existing
  plugin).
- Remind the user that **function names are a global namespace**: registering a
  name already claimed by a different file is a hard error. They will pick
  distinctive function names later in `/occ_new-function`.

## Step 3 — Create the package skeleton

Create exactly these files (everything is empty unless shown):

```
opencellcomms_adapters/<name>/
├── __init__.py                      # empty
├── plugin.toml                      # manifest (below)
├── register.py                      # imports the plugin's functions (below)
├── requirements.txt                 # only if extra libraries were named (below)
└── functions/
    ├── __init__.py                  # empty
    └── <role>/                      # one per role from Step 1 (optional)
        └── __init__.py              # empty
```

All `__init__.py` files are **empty** (match the existing plugins — they carry no
code). Only create `functions/<role>/` folders for roles the user named; skip if
they named none.

**`plugin.toml`** — seed the manifest:

```toml
# OpenCellComms plugin manifest. See docs/PLUGINS.md for the full schema.
[plugin]
name = "<name>"
version = "0.1.0"
description = "<one-line description>"
author = "<author>"
engine_version = ">=0.0.0"
compatible_kernels = <["*"] or ["biophysics"]>
```

**`register.py`** — importing this file is what registers the plugin's functions.
Start it with a docstring and no imports yet (an empty `register.py` still loads
and is enough for discovery). `/occ_new-function` and the GUI's **Export Behavior**
append the per-function imports here later:

```python
"""
<name> adapter.

<one-line description>

Importing this module runs each function's @register_function decorator.
The engine auto-discovers this file on startup (see docs/PLUGINS.md). Add one
import per function here as you author them, e.g.:

    import opencellcomms_adapters.<name>.functions.<role>.<fn>  # noqa: F401
"""
```

Use the `import ... # noqa: F401` style (matches existing plugins). Either that
or `from ... import <fn>` is accepted by discovery; pick one and be consistent.

**`requirements.txt`** — create this **only if** the user named extra libraries in
Step 1. One pip requirement per line:

```text
# extra libraries this plugin needs
<lib>>=<version>
```

Every install path auto-installs each plugin's `requirements.txt` — `install.sh`,
`install.bat`, and the Docker backend image all loop over
`opencellcomms_adapters/*/requirements.txt`. So **do not edit the installer
scripts or the Dockerfile** for pip packages. After creating/changing it, tell the
user how to apply it:
- **Native:** re-run `./install.sh` (or `install.bat` on Windows).
- **Docker:** rebuild with `docker compose up --build`.
- Then restart the backend so the new functions register.

A library that needs a *system* (apt) package is the one manual case — see
`docs/PLUGINS.md` → **Dependencies** (document it in the plugin README for native
installs, and add it to `Dockerfile.backend`'s `apt-get` line for Docker).

## Step 4 — Confirm and hand off

Tell the user:
- The plugin path: `opencellcomms_adapters/<name>/`
- That it is **auto-discovered on the next backend restart** — no `registry.py`
  edit, no hardcoded list (this is the whole point of the plugin model).
- Restart with `./run.sh` (or Ctrl+C then `./run.sh`).
- **If you created a `requirements.txt`:** re-run the installer (`./install.sh` /
  `install.bat`) — or `docker compose up --build` for Docker — *before* the
  restart, so the new libraries are installed.
- Verify it loaded: `GET http://localhost:5001/api/plugins` (if the backend is
  running) should list it, or from `opencellcomms_engine/`:
  ```bash
  python -c "from src.workflow.registry import get_default_registry; get_default_registry(); import opencellcomms_adapters.<name>.register"
  ```
- Next steps:
  - Add a biological function: `/occ_new-function`
  - Assemble a runnable workflow once it has behaviors: `/occ_create-workflow`

## Notes

- `behaviors/` (exported `.subworkflow.json` files) and `workflows/` (top-level
  workflow JSON) folders are **not** created now — they appear when the user
  exports a behavior or runs `/occ_create-workflow`. Don't pre-create them.
- The shared biology primitives live in the `common` plugin; experiment plugins
  may import from it. You do not need to depend on it to start.

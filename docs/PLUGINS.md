# Plugins (Adapters)

A **plugin** is a self-contained package of simulation functions you can share,
cite, run, and fork — a biological model expressed as code. If you've used
Fiji/ImageJ or Napari plugins, this is the same idea: the OpenCellComms engine is
a thin core (kernel + spatial solvers + IO), and everything that creates or
evolves cells, gene networks and behaviours arrives as a plugin.

> **Terminology.** "Plugin" is the user-facing name. In the codebase and on disk
> the same thing is called an **adapter** and lives in `opencellcomms_adapters/`.
> The two words are interchangeable.

The shared biology primitives (gene networks, metabolism, cell lifecycle) are
themselves a plugin — `opencellcomms_adapters/common/` — that the experiment
plugins build on.

---

## Anatomy of a plugin

```
opencellcomms_adapters/<plugin_name>/
├── plugin.toml                      # manifest (identity + contract)
├── register.py                      # imports the plugin's functions
├── requirements.txt                 # optional: extra pip libraries this plugin needs
├── __init__.py
└── functions/
    ├── __init__.py
    ├── <model_role>/<fn>.py         # one file = one function
    └── <model_role>/<fn>.py
```

- **`plugin.toml`** — the manifest (see below). Gives the plugin an identity.
- **`register.py`** — a list of imports; importing it runs each function's
  `@register_function` decorator, registering it. The engine imports this file
  automatically (see [Discovery](#discovery)).
- **`requirements.txt`** *(optional)* — extra pip libraries the plugin needs;
  every installer and the Docker image install it automatically (see
  [Dependencies](#dependencies-extra-python-libraries)).
- **`functions/<model_role>/<fn>.py`** — one function per file (so each is
  readable and editable in the GUI). Use folders that describe the model role,
  such as `agent_behavior`, `resource_behavior`, `sugar`, or `forager`.

Older plugins may still use folders such as `initialization`, `intracellular`,
`intercellular`, `diffusion`, and `finalization`. Treat those as legacy registry
categories, not as a required plugin taxonomy.

The folder name must be a valid Python identifier (letters, digits, underscores;
not starting with a digit). Names with other characters — e.g.
`jayatilake_(legacy)` — are skipped by discovery and kept on disk for reference
only.

---

## The manifest: `plugin.toml`

```toml
# OpenCellComms plugin manifest.
[plugin]
name = "MicroC"                       # plugin name (usually the folder name)
version = "0.1.0"                     # semantic version
description = "MicroC metabolic ABM."  # one-line summary (shown in the GUI)
author = ""                           # who maintains it
engine_version = ">=0.0.0"            # engine versions this works with
compatible_kernels = ["biophysics"]   # kernels this plugin targets; ["*"] = any
```

| Field | Meaning |
|---|---|
| `name` | Plugin name (display + identity). |
| `version` | Semantic version of the plugin. |
| `description` | One-line summary surfaced in the GUI plugin picker. |
| `author` | Maintainer. |
| `engine_version` | Engine version range the plugin is known to work with. |
| `compatible_kernels` | Kernels the plugin's functions target. `["*"]` = all. |

The manifest is **optional for loading** — a plugin with only a `register.py`
still loads — but it's how the plugin gets a real identity, and it's what
`GET /api/plugins` reports. New plugins created through the GUI get a manifest
seeded automatically.

---

## Dependencies (extra Python libraries)

If your plugin needs a Python library the engine doesn't already ship — a special
solver, a file-format reader, a stats package — declare it in a **`requirements.txt`**
at the plugin root:

```text
# opencellcomms_adapters/<name>/requirements.txt — one pip requirement per line
networkx>=3.0
openpyxl
```

You do **not** edit the installer scripts or the Dockerfile: every install path
already loops over `opencellcomms_adapters/*/requirements.txt` and installs each one.

| Install path | Picks up `requirements.txt`? | Apply a new/changed library by |
|---|---|---|
| `install.sh` (macOS/Linux) | ✅ automatically | re-running `./install.sh` |
| `install.bat` (Windows) | ✅ automatically | re-running `install.bat` |
| `Dockerfile.backend` / `docker compose` | ✅ automatically (at image build) | rebuilding: `docker compose up --build` |

So the loop is: **add the line → re-install (native) or rebuild (Docker) →
restart the backend** so the new functions register.

> If a plugin's `requirements.txt` install *fails* (e.g. a wheel won't build), the
> installers print a warning and **continue** — that plugin is skipped at runtime
> rather than breaking the whole install. Keep requirements lean and prefer
> packages with prebuilt wheels so they install cleanly on every OS.

### System (non-pip) dependencies

A few libraries need an OS-level package (a C library, a compiler) that pip can't
install:

- **Native installs:** name the OS package in your plugin's README (e.g.
  `sudo apt install libfoo-dev`, or the macOS/Windows equivalent) so users add it
  before running the installer.
- **Docker:** add it to the `apt-get install` line in **`Dockerfile.backend`** —
  the one place a system dependency is hand-edited — then rebuild.

---

## Discovery

On startup the engine **auto-discovers** plugins — there is no hand-maintained
list. `registry.py` (`discover_adapter_names()` → `get_default_registry()`)
imports the `register.py` of every folder under `opencellcomms_adapters/` that:

1. has a `register.py`, and
2. has a Python-importable name (a valid identifier).

`common` is imported first because the experiment plugins import from it.

**This means a newly created plugin works on the next backend restart with zero
edits to engine code.** (Previously the list was hardcoded, so new plugins
vanished on restart.)

---

## Function naming & collisions

Function names are a **global namespace** — workflows resolve functions by name.
To stop two plugins from silently shadowing each other:

- Registering a name already claimed by a **different source file** is a
  **hard error** when a plugin is involved. The registry fails loudly instead of
  silently picking whichever loaded last.
- Re-registering the same name from the **same file** is fine (a module reload
  re-runs the decorator), so the GUI's live-reload path is unaffected.
- Two **engine-core** files sharing a name only *warn* (a small set of
  pre-existing duplicates is tracked for cleanup).

Pick distinctive function names. If two plugins genuinely need the same concept,
give the functions different names (e.g. `microc_mark_necrotic` vs
`mark_necrotic_cells`).

---

## Engine vs plugin: where does my function go?

| | Engine (`opencellcomms_engine/src/workflow/functions/`) | Plugin (`opencellcomms_adapters/<name>/`) |
|---|---|---|
| **What** | Generic, reusable machinery: diffusion solvers, IO, kernel setup | A specific biological model / experiment |
| **Examples** | `run_diffusion_solver`, `export_vtk` | hardcoded gene names, substance thresholds, model-specific fate rules |
| **Registration** | Add to the appropriate core import path (pulled in via `standard_functions.py`) | Add to the plugin's `register.py` (auto-discovered) |
| **Audience** | Engine developers | Biologists & biologist-developers |

When in doubt, **make it a plugin**. Plugins are the path designed for sharing
and for the GUI.

---

## Creating a plugin

### From the GUI (recommended)

On a behaviour/init canvas: **Library → New Function**. In the dialog:

1. Enter the function **name** and pick the **role**.
2. Under **Plugin**, pick an existing plugin or choose **➕ New plugin…** and
   type a name. The file path is *derived* for you — you never type a raw path.
3. Declare what the function reads (capability checkboxes → `requires`), or tick
   *setup function* for population/file-loading code.
4. **Add to Project**, then **Export Behavior** on the canvas to write the file.

Exporting a function into a new plugin scaffolds the whole package — `__init__.py`
files, `register.py`, and a seeded `plugin.toml` — so it's import-ready and
survives a restart.

### By hand

1. Create `opencellcomms_adapters/<name>/` with `__init__.py`, `register.py`, and
   a `plugin.toml`.
2. Add function files under a model-role folder such as
   `functions/agent_behavior/`, `functions/resource_behavior/`, or a
   domain-specific folder such as `functions/forager/`, using the typed `env`
   template (see `opencellcomms_engine/src/workflow/functions/_TEMPLATE.py` and
   [docs/BIOLOGICAL_CONTEXT.md](BIOLOGICAL_CONTEXT.md)).
3. Import each function in `register.py`:
   `from opencellcomms_adapters.<name>.functions.<model_role>.<fn> import <fn>`
4. Restart the backend — the plugin is discovered automatically.

---

## Inspecting installed plugins

`GET /api/plugins` returns every discovered plugin with its manifest and the
functions it owns:

```json
{
  "success": true,
  "count": 4,
  "plugins": [
    { "name": "MicroC", "path": "opencellcomms_adapters/MicroC",
      "has_manifest": true,
      "manifest": { "version": "0.1.0", "compatible_kernels": ["biophysics"] },
      "functions": ["mark_necrotic_cells", "..."] }
  ]
}
```

The GUI's New Function dialog uses this endpoint to populate its plugin picker.

---

## See also

- [BIOLOGICAL_CONTEXT.md](BIOLOGICAL_CONTEXT.md) — the typed `env` authoring API
- [CREATING_FUNCTIONS.md](CREATING_FUNCTIONS.md) — writing a function in detail
- [SHARING_GUIDE.md](SHARING_GUIDE.md) — sharing your work as a plugin
- `opencellcomms_engine/src/workflow/functions/_TEMPLATE.py` — the canonical template

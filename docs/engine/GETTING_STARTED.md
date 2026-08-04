# Getting Started with OpenCellComms 2.0

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm 7+
- Git

## Install

From the repository root, use the platform installer:

```bash
./install.sh
```

On Windows, run `install.bat`. The installer creates `.venv`, installs the
engine with its active FiPy/MaBoSS extras, installs the local Flask backend, and
installs the GUI packages.

For a manual engine-only development install:

```bash
python3 -m venv .venv
source .venv/bin/activate
cd opencellcomms_engine
pip install -e ".[dev,diffusion,maboss]"
```

## Verify

```bash
occ-run --help
make test-fast
```

The first command works outside the repository after installation. The second
command is run from `opencellcomms_engine/` (or as `make test-fast` from the
repository root).

## Run a canonical workflow

```bash
occ-run --workflow opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json
```

Configuration-driven mode is separate and mutually exclusive:

```bash
occ-run --sim opencellcomms_engine/src/config/simple_oxygen_glucose.yaml
```

Results are written below the repository-level `runs/` tree. For workflow
authoring and model-specific guidance, continue with:

- [Usage guide](../USAGE.md)
- [Plugin guide](../PLUGINS.md)
- [Biological context API](../BIOLOGICAL_CONTEXT.md)
- [Engine README](../../opencellcomms_engine/README.md)

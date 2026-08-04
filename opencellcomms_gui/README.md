# OpenCellComms GUI

The React/React Flow authoring interface for OpenCellComms v2 workflows.

## Development

Prerequisites are Node.js 18+ and npm. From this directory:

```bash
npm install
npm run dev
```

Vite serves the GUI at `http://localhost:3000`. The Flask backend is local-only
at `http://127.0.0.1:5001`. To use another backend URL, set it before starting
or building the GUI:

```bash
VITE_API_URL=http://127.0.0.1:5001 npm run dev
```

The frontend shows an explicit backend-unavailable notice if the live function
registry cannot be loaded; it does not substitute an offline registry.

## Checks

```bash
npm run lint
npm run build
```

## Authoring model

The navigable views are Overview, Agents, Resources, World, Initialization,
Scheduler, Planner, Processing, and Results. Workflows are v2 JSON documents
made of named subworkflows, ordered function nodes, and subworkflow calls.

Use the repository's canonical examples as templates:

- `opencellcomms_adapters/MicroC/workflows/microc.json`
- `opencellcomms_adapters/TCELL_CORRAL/workflows/tcell_corral.json`
- `opencellcomms_adapters/SUGARSCAPE/workflows/sugarscape.json`

Exported workflows run through the installed CLI:

```bash
occ-run --workflow path/to/workflow.json
```

See [the usage guide](../docs/USAGE.md), [the plugin guide](../docs/PLUGINS.md),
and [the biological context API](../docs/BIOLOGICAL_CONTEXT.md) for details.

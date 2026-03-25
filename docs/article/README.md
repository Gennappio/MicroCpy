# OpenCellComms — Article Draft (Chapter Files)

This folder contains a **chapter-per-file** long-form article draft about the software in this repository:
- **Python simulation engine**: `opencellcomms_engine/`
- **Visual workflow designer (GUI)**: `opencellcomms_gui/`

The writing is intended to be copy/pasted into a blog platform, report, or thesis chapter structure.

## Suggested chapter order

1. `01-executive-summary-and-positioning.md`
2. `02-the-problem-and-why-workflows.md`
3. `03-system-overview-and-architecture.md`
4. `04-workflow-language-and-execution-model.md`
5. `05-simulation-engine-models-and-algorithms.md`
6. `06-visual-workflow-designer-and-backend-api.md`
7. `07-observability-debuggability-and-scientific-ux.md`
8. `08-reproducibility-results-and-data-products.md`
9. `09-limitations-tradeoffs-and-future-work.md`
10. `10-hands-on-walkthrough-with-example-workflows.md`
11. `11-extending-the-platform-custom-functions.md`

## How to use

- **Write once, publish many**: each chapter stands alone (it repeats minimal context), but they also flow as a single narrative.
- **Consistent branding**: the project is called OpenCellComms. Legacy references to MicroCpy or BioComposer may appear in older drafts.
- **Replace figure placeholders**:
  - “Suggested figure” sections describe what to capture.
  - When possible, they point at **existing artifacts already in this repo** (plots in `opencellcomms_gui/results/` and `opencellcomms_engine/tools/*results/`).

## Notes on scope and assumptions

- The repository does not currently contain `code_description.txt` or `code_activities.txt` (mentioned in your rules). The draft therefore anchors itself to existing docs:
  - `README.md`, `docs/*`, `opencellcomms_engine/README.md`, `opencellcomms_gui/README.md`, and `opencellcomms_gui/NODES_OBSERVABILITY.md`.


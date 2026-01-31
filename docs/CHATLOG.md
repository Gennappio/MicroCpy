# Chatlog (assistant traceability)

This file tracks significant assistant-driven changes for traceability.

## 2026-01-28

- Added `docs/article/` chapter-per-file long-form article draft and `docs/tech_details.md` technical deep dive for LLM-friendly onboarding.
- Added `docs/context_enforcement.md` explaining `ValidatedContext` write policies, motivations, and use cases.

## 2026-01-30

- Added `docs/@microc-2.0/docs/MicroC_GUI_Workflow_Building_Chapter.txt`: deep, step-by-step documentation of the GUI workflow `microc_relaxation_workflow_v3.json`, emphasizing the one-step equilibrium design and the FiPy steady-state + Picard coupling with under-relaxation (“relaxation”) method.
- Expanded `docs/@microc-2.0/docs/MicroC_GUI_Workflow_Building_Chapter.txt` with workflow JSON excerpts and key engine code snippets (FiPy equation, coupled solver loop, metabolism coupling, position→grid mapping) to make the narrative directly traceable to implementation.


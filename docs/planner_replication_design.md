# Planner replication design (historical)

This proposal has been superseded by the implemented, simpler Planner described
in [Replication and reproducibility in Planner](PLANNER_REPLICATION.md). The
workflow JSON now stores the complete editable plan: configurations, replicate
counts and seed settings. Runtime metadata inside a results folder is an
automatic execution record, never a second plan to prepare, import or edit.

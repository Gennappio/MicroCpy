# Chapter 7 — Observability, Debuggability, and Scientific UX

## 7.1 Why observability matters more in scientific simulation

In many software products, the primary question is:

- “Is it up?”

In scientific simulation, the primary questions are closer to:

- “Why did the behavior change?”
- “Which part of the pipeline caused this effect?”
- “Did we just violate an assumption without noticing?”

Simulation failures are often not stack traces—they are wrong results.

That is why OpenCellComms treats observability as a first-class feature rather than a logging afterthought.

## 7.2 The project’s explicit philosophy: scientific tool, not enterprise software

The observability specification in `opencellcomms_gui/NODES_OBSERVABILITY.md` is unusually explicit about product stance:

- prioritize **simplicity** and “features that help debugging”
- prefer **flat files** over databases
- avoid run-history features, quotas, migrations, and other complexity
- assume researchers will archive results they care about

This is a sensible choice for a research-focused tool because it:

- reduces engineering complexity,
- keeps artifacts inspectable,
- and makes the debugging experience “close to the data.”

The tradeoff is also explicit:

- you do not get a built-in run history unless you copy/backup results directories.

## 7.3 Node-level observability: the right unit of debugging

Because simulations are workflows, the natural debugging unit is a **node execution**:

- node start/end
- elapsed time
- status (ok/warn/error/skipped)
- logs attached to that node
- context reads/writes attributable to the node

This is more actionable than “the simulation printed a bunch of lines,” because it connects behavior to a specific part of the protocol.

## 7.4 Immutable context snapshots: “time travel” for workflow state

A major design concept is **immutable context** versions:

- before a node executes: snapshot version \(N\)
- after a node executes: snapshot version \(N+1\)
- compute a diff between them

This gives the user a concrete answer to:

> “What changed because of this node?”

It also makes debugging reproducible:

- the inspector reads stored snapshots rather than a volatile live object.

## 7.5 Tracked context reads/writes: observability without guesswork

The spec argues for explicit tracking rather than heuristics:

- wrap the context dict in a `TrackedContext` implementation
- emit events for reads/writes

This matters because it turns “debugging by rumor” into “debugging by evidence”:

- which keys did the node read?
- which keys did the node write?

Even if you don’t expose all details in the UI, collecting them makes future debugging tools possible.

## 7.6 UX patterns: badges + inspector

The observability UX described in the spec includes:

- **inline node badges** (status, timing, warnings/errors, context-delta counts)
- a **node inspector** with tabs:
  - overview
  - parameters (resolved)
  - context (before/after + diff)
  - logs (filtered)
  - artifacts

This is a strong scientific UX pattern because it keeps “what happened” adjacent to “what the model is.”

## 7.7 Practical constraints: large values, big runs

Scientific simulations produce large intermediate structures:

- arrays (fields, matrices)
- big dicts (population state)
- large log streams

The spec addresses this with:

- preview-first rendering
- truncation limits (e.g., 10KB inline)
- pointers to artifacts for full materialization (with max size limits)
- pagination for event streams

This is not glamorous, but it is essential if you want observability to work beyond toy examples.

## 7.8 Suggested figures (for this chapter)

- **Figure 1 — Screenshot: node badges**
  - Show multiple nodes with different statuses (ok/warn/error) and timing badges.

- **Figure 2 — Screenshot: inspector Context tab**
  - Show “before/after” snapshots and a diff view for a node execution.

- **Figure 3 — Data layout diagram**
  - Depict a `results/observability/` folder containing:
    - `events.jsonl`
    - `context/<scope>/v000123.json`
    - `diff/`
    - `artifacts/`
  - Emphasize “overwritten per run” semantics.


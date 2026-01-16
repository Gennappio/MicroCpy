# Node Observability (GUI + Runtime) — Specification

## 1) Purpose
Node Observability provides **node-level introspection** while designing and running workflows:
- **Node Inspector**: inspect node configuration + runtime behavior.
- **Inline badges** on canvas nodes: last status, timings, logs, warnings.
- **Immutable Context vs Mutable Context**: time-travelable context snapshots per node execution.
- **Value inspection**: browse large structured values safely (preview + paging).
- **Per-node logging**: filter logs by node, stage/subworkflow, and call path.

This spec targets the **MicroC Workflow Designer (ABM_GUI)** + MicroC runtime instrumentation.

---

## 1.1) Design Philosophy: Scientific Tool, Not Production Software

MicroC is a **scientific research tool**, not enterprise production software. This distinction drives key design decisions:

### Simplicity over features
- Researchers need to **debug and understand** their simulations, not manage infrastructure.
- Every feature must earn its complexity. If it doesn't help debugging, it doesn't belong.
- "Good enough" solutions that work today beat "perfect" solutions that delay progress.

### User responsibility model
- **The user is responsible for saving important results.** The system does not maintain run history.
- Each new run **overwrites** the previous observability data. This is intentional.
- If a researcher wants to preserve a run, they copy/backup the results directory.
- This avoids: run management UI, storage quotas, cleanup policies, database migrations.

### Escape hatches over configurability
- Default behavior should be **maximum debuggability** (e.g., snapshot every node).
- If defaults are too heavy, users can: disable snapshots, use a debug node, or add manual logging.
- We don't need settings panels for every edge case.

### Implications for this spec
- No `runId` tracking or history — only "current run" matters.
- No complex caching strategies — reload clears state, that's fine.
- No database — flat files (JSONL, JSON) are sufficient and inspectable.
- Inspector is a debugging aid, not a monitoring dashboard.

---


## 2) Goals / Non-goals
### Goals
1. **Single source of truth** for selection + observability UI state (Zustand).
2. **Deterministic context history**:
   - each node execution produces an immutable “context version”.
   - diffs between versions are available.
3. **Cross-subworkflow tracing** through SubWorkflowCall nodes (call stack).
4. **Low-friction UX**: click node → inspector opens with meaningful defaults.
5. **Scalable** to large runs: streaming/pagination, value truncation.

### Non-goals (v1)
- Live, per-cell step debugging at interactive framerates for million-cell runs.
- Arbitrary code evaluation in the inspector.
- Run history or comparison between runs (user saves what they need).

## 3) Terminology
- **Stage / Subworkflow**: GUI tab (e.g., `initialization`, `intracellular`, or composer `main`).
- **Scope**: `(subworkflowKind, subworkflowName, [nodeId], [callPath])`.
- **Run**: one simulation execution producing observability artifacts.
- **Context**: key-value store used by executor.
  - **Mutable Context**: runtime map during execution.
  - **Immutable Context**: persisted snapshot (versioned) after each node.
- **NodeEvent**: structured record emitted by runtime (logs, timing, reads/writes).

Design principles used throughout this spec:
1. **Ephemeral UI state vs persisted run artifacts**
   - selections (node/cell) are ephemeral and live only in the GUI store
   - observability artifacts (events/snapshots/diffs) are persisted as part of a run
2. **Stable identifiers**
   - every record is keyed by stable IDs: `scopeKey`, `nodeId`, `executionId`
3. **Preview-first for large values**
   - large values are summarized; full values require explicit user action
   - 10KB inline limit; larger values use artifact pointers; 1MB max per artifact
4. **Read-only observability**
   - the inspector must not mutate simulation state or workflow JSON
5. **Context key naming conventions**
   - Use prefixes: `node:*` (node-local), `sim:*` (simulation state), `user:*` (user-defined)

## 4) UX Requirements
### 4.1 Canvas inline badges
Each node renders a compact badge strip:
- **Status**: `idle | running | ok | warn | error | skipped`.
- **Timing**: last duration ms (and optional avg/p95).
- **Logs**: count by level (info/warn/error) for current run.
- **Context delta** indicator: number of keys written.

Interactions:
- Hover: tooltip with last execution summary.
- Click: selects node + opens Inspector.
- Double click: existing parameter editor behavior remains.

Badge visual language (v1):
- Status color mapping:
  - `idle/never-run`: neutral gray
  - `running`: blue
  - `ok`: green
  - `warn`: amber
  - `error`: red
  - `skipped/disabled`: muted
- Status precedence if multiple executions exist:
  - `error` > `warn` > `running` > `ok` > `skipped` > `idle`
- Log badge precedence:
  - if `errorCount>0`, show error badge (and optionally total)
  - else if `warnCount>0`, show warn badge
  - else hide the log badge (optional) to reduce noise

Badge click-to-tab behavior (quality-of-life):
- click status/timing → open Inspector on **Overview**
- click context-delta → open Inspector on **Context**
- click log badge → open Inspector on **Logs**

### 4.2 Node Inspector (right panel or modal)
Tabs (minimum):
1. **Overview**: id, function name/file, enabled, stage, call path, last status/timing.
2. **Parameters**: resolved parameters (incl. parameter-node merges).
3. **Context**:
   - “Before” snapshot (immutable version N)
   - “After” snapshot (immutable version N+1)
   - **Diff view** (added/changed/removed keys)
   - Key search + type badges.
4. **Logs**: per-node filtered logs, level toggles, copy/export.
5. **Artifacts**: links/previews to produced files (plots, csv, vtk, etc.) when traceable.

Execution instance selection (required):
- Default: show **latest** execution for the selected node in the **active run**.
- User can switch among:
  - `executionId` (timeline / dropdown)
  - `stepIndex`/`time` (when present)
  - `callPath` instance (when node executed inside nested subworkflow calls)

Inspector focus behavior:
- Selecting a node changes Inspector focus *unless* Inspector is "pinned".
- When pinned, node selection still updates global store state and badges, but Inspector stays on the pinned node.

### 4.3 Value inspection (deep viewer)
The Inspector exposes a Value Viewer for:
- context keys (before/after)
- diff entries (before/after)
- produced values

Requirements:
1. Preview-first rendering (type + summary)
2. Expand/collapse structured values (objects/arrays)
3. Safe handling of large payloads (no full render by default)
4. Chunked loading for large arrays/records
5. Type-specialized viewers where possible (JSON tree, table, image, text)

### 4.4 Immutable Context vs Mutable Context (UX)
The Context tab supports two modes:
1. **Immutable snapshots** (default):
   - “Before” and “After” are versioned snapshots tied to a specific node execution.
   - Always reproducible for `(runId, scopeKey, version)`.
2. **Mutable live context** (optional; phase B+):
   - shows the current in-memory context while a simulation is running.
   - clearly labeled as LIVE, and may be partial/truncated.

Rules:
- Immutable snapshot is the *source of truth* for debugging.
- Live view is best-effort and must never be conflated with an immutable version.

### 4.5 Cell/Data selection (ephemeral)
Grid-like viewers (future/optional) must support selecting cells/rows.
Selection is **scoped** and persisted ephemerally:
- Scope key format: `"kind:subworkflow"` or `"kind:subworkflow:nodeId"` (+ optional callPath later).
- Selection should not pollute workflow JSON.

Selection semantics:
- Single click selects a row.
- Shift-click selects a range.
- Cmd/Ctrl-click toggles rows.
- A per-scope "Clear selection" action exists.

## 5) Data Model (frontend)
### 5.1 Zustand additions (existing pieces may already exist)
State:
- `selectedNodeByStage: { [stage]: nodeId|null }` *(already exists)*
- `cellSelectionByScope: { [scopeKey]: string[] }` *(already exists)*
- `nodeBadgeStatsByScope: { [scopeKey]: { [nodeId]: BadgeStats } }`
- `inspector: { isOpen: boolean, tab: 'overview'|'params'|'context'|'logs'|'artifacts' }`
- `lastRunMeta: { startedAt: string, status: string } | null`

Recommended additional state (v1):
- `activeExecutionByNode: { [scopeKey]: { [nodeId]: executionId|null } }`
- `inspectorPinned: boolean`

Note: No complex caching strategy needed — reload clears state, that's fine for a scientific tool.

Actions:
- `setSelectedNode(stage,nodeId)` / `clearSelectedNode(stage)` *(already exists)*
- `resolveScopeKey(kind,subworkflow,nodeId?)`
- `setCellSelection(scopeKey,ids)` (+ add/remove/clear)
- `fetchNodeBadgeStats(scope)` (async)
- `setInspectorTab(tab)` / `toggleInspectorPinned()`

BadgeStats:
- `status, lastStart, lastEnd, lastDurationMs`
- `logCounts: {info,warn,error}`
- `writes: number` (keys written)

### 5.2 Scope resolution rules
Given GUI context:
- `stage` = current canvas stage name
- `kind` = `workflow.metadata.gui.subworkflow_kinds[stage]` (fallback: `stage==='main'?'composer':'subworkflow'`)
- `nodeId` = selected node id for stage (optional)

Scope keys:
- Stage scope: `kind:stage`
- Node scope: `kind:stage:nodeId`

Future (phase B+): allow callPath-qualified scope keys (encoding TBD, must be URL-safe).

### 5.3 Caching strategy (frontend)
Keep it simple:
- No persistent cache across page reloads.
- In-memory cache for current session only.
- Query key format: `scopeKey + '|' + nodeId + '|' + levelMask`
- On new run, clear all cached observability data.

## 6) Runtime Instrumentation Requirements
### 6.1 Events
Executor emits NodeEvents (JSONL) with fields:
- `ts, level, kind`
- `subworkflowKind, subworkflowName`
- `nodeId, nodeType, functionName`
- `traceId, parentTraceId, callPath[]`
- `event: 'node_start'|'node_end'|'context_read'|'context_write'|'log'|'artifact'`
- `payload` (see below)

Note: No `runId` in events — there's only one run's data (overwritten each time).

Minimum payloads (v1):
- `node_start`: `{ executionId, stepIndex?, time?, beforeContextVersion }`
- `node_end`: `{ executionId, status, durationMs, afterContextVersion, writtenKeys?, readKeys? }`
- `log`: `{ executionId?, message, loggerName?, source? }`
- `artifact`: `{ executionId?, path, mime, label? }`

### 6.1.1 NodeEvent schema (informal)
NodeEvent fields should be treated as a stable contract:
- `ts`: ISO8601 string (preferred) or unix millis (but be consistent)
- `level`: `DEBUG|INFO|WARN|ERROR`
- `kind`: `composer|subworkflow` (subworkflow kind)
- `nodeType`: `workflowFunction|controller|parameter|subworkflowCall|group` (GUI taxonomy)

Event ordering:
- events in `events.jsonl` are append-only
- consumers should not assume strict ordering across threads/processes; sort by `(ts, traceId)` if needed

### 6.2 Context versioning
- Maintain `contextVersion` integer per scope.
- On `node_start`: record `beforeVersion`.
- On `node_end`: compute `afterVersion = beforeVersion + 1` **if any writes**, else may keep same.
- Persist snapshots as:
  - `context/<scope>/v000123.json` (or msgpack) with metadata + truncated values.
  - `context/<scope>/diff/v000122_to_v000123.json` for quick diff.

Diff format:
- `added: {k:summary}`
- `changed: {k:{before:summary, after:summary}}`
- `removed: {k:summary}`

Value summary rules:
- Scalars stored fully.
- Large arrays/strings stored as preview + byte/len + optional artifact pointer.

### 6.2.2 ValueSummary contract
Every value in a snapshot/diff should be representable as a `ValueSummary`:
- `type`: string (e.g., `number`, `string`, `list`, `dict`, `ndarray`, `DataFrame`)
- `shape`: optional (for arrays)
- `len`: optional (for sequences)
- `preview`: small JSON-serializable preview
- `truncated`: boolean
- `pointer`: optional string referencing an artifact for full materialization

Materialization rules:
- If `pointer` is present, the UI may fetch the full value through `/api/observability/artifact`.
- If `truncated=true` and no pointer is provided, the full value is considered unavailable.

### 6.2.1 Immutable vs mutable representation
- Runtime maintains a mutable in-memory context.
- Immutable versions are persisted snapshots.
- GUI must treat snapshots as authoritative; live context is best-effort.

### 6.3 Per-node logging
- All existing logs can be attached to a `traceId` and optionally `nodeId`.
- Provide level + source (python module/function).
- Logs are queryable by `(scope, nodeId)`.

Logging level policy:
- runtime emits at least `INFO/WARN/ERROR` (optionally `DEBUG`)
- UI defaults to `INFO+` and allows enabling `DEBUG`

### 6.4 Context read detection
Use **explicit tracking** (wrapped dictionary) rather than heuristics:
- Wrap the context dict with a `TrackedContext` class that logs all `__getitem__` calls.
- This provides accurate read tracking without parsing source code.

### 6.5 Snapshot frequency
Default: **snapshot before and after every node execution**.
- Provides maximum debuggability.
- If too heavy, user can disable via workflow settings or use manual logging.
- Phase B+: configurable per-node or per-subworkflow.

### 6.6 Storage layout (results directory)
Observability artifacts are stored in a **fixed location** (overwritten each run):
```
results/observability/
├── run_meta.json                           # { startedAt, status, entrySubworkflow }
├── events.jsonl                            # All NodeEvents, append-only during run
├── context/
│   ├── composer:main/
│   │   ├── v000001.json                    # Snapshot version 1
│   │   ├── v000002.json
│   │   └── diff/
│   │       └── v000001_to_v000002.json
│   └── subworkflow:intracellular/
│       └── ...
└── artifacts/                              # Large values, plots referenced by pointer
    └── ...
```

**Note:** No `runId` subdirectory. Each run overwrites the previous. User backs up `results/` if needed.

## 7) Backend API (ABM_GUI/server)
Required endpoints (read-only, all operate on "current run" data):
- `GET /api/observability/meta` → run metadata (startedAt, status).
- `GET /api/observability/nodes?subworkflowKind&subworkflowName` → node stats for badges.
- `GET /api/observability/events?scopeKey&nodeId&cursor&limit` → paged events.
- `GET /api/observability/context?scopeKey&version` → snapshot.
- `GET /api/observability/diff?scopeKey&from&to` → diff.
- `GET /api/observability/artifact?path` → fetch artifact/preview.

### 7.1 Endpoint parameter semantics
- `scopeKey`: required for endpoints dealing with context/events.
- `nodeId`: optional for `/events` (if omitted, returns all events in scope).
- `cursor`/`limit`: pagination for event streams (limit defaults to 200; max 2000).

Error semantics:
- `{ success:false, error:'...' }` for functional errors
- HTTP status codes should still be meaningful (`404` data not found, `400` bad query, `500` server error)

### 7.2 Typical UI data flow
1. User starts a run → observability directory is cleared and run begins.
2. Canvas requests badge stats for the current stage scope.
3. User clicks a node → GUI sets `selectedNodeByStage[stage]=nodeId` and opens Inspector.
4. Inspector requests:
   - latest execution metadata
   - before/after snapshot + diff
   - node-scoped logs/events
5. User clicks a context key → Value Viewer either:
   - renders inline preview (from snapshot), or
   - fetches full value via artifact pointer

API behavior requirements:
- all endpoints are read-only and safe to retry
- cursor pagination is stable within a run
- server indicates truncation for large values

Recommended response shapes (informal):
- `/meta` → `{ success, startedAt, status, entrySubworkflow }`
- `/nodes` → `{ success, nodes:{[nodeId]: BadgeStats} }`
- `/events` → `{ success, events: NodeEvent[], nextCursor }`
- `/context` → `{ success, snapshot }`
- `/diff` → `{ success, diff }`

## 8) Implementation Phases

### Phase A (MVP)
- Runtime: NodeEvent emission (`node_start`, `node_end`, `log`)
- Runtime: Context snapshotting (before/after each node)
- Runtime: TrackedContext for read detection
- Backend: `/api/observability/*` endpoints
- Frontend: Node badges (status, timing, log counts)
- Frontend: Inspector panel (Overview, Logs tabs)
- Frontend: Basic Context tab (before/after/diff view)

### Phase B
- Artifact linking (plots, files traceable to nodes)
- Cross-subworkflow callPath tracing
- Parameters tab (resolved parameters)
- Artifacts tab (links to produced files)

### Phase C
- Grid viewer for array-type context values
- Cell selection scoped per node
- Per-cell value sampling + aggregates

## 9) Acceptance Criteria
1. Clicking a node shows Inspector with last status/timing (if a run exists).
2. Badge counts match per-node filtered logs.
3. Context tab shows diff between before/after for a node execution.
4. Selection state persists across tab changes but resets on reload (ephemeral).
5. Inspector is a collapsible right panel, not a modal.

## 10) Design Decisions (Confirmed)

| # | Question | Decision |
|---|----------|----------|
| 1 | Cell Table data source | CSV checkpoints (start simple) |
| 2 | Per-cell values | Use sampling + aggregates to avoid explosion |
| 3 | Context key naming | Prefix convention: `node:*`, `sim:*`, `user:*` |
| 4 | Payload limits | 10KB inline, pointer above; 1MB max per artifact |
| 5 | Run tracking | **No runId** — overwrite each run, user saves what they need |
| 6 | Snapshot frequency | Every node (Phase A), configurable later |
| 7 | Context read detection | Explicit tracking via TrackedContext wrapper |
| 8 | Inspector placement | Right panel, collapsible (not modal) |

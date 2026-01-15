# Context Management (Project‑Scoped + Strict Registry) — Canonical Specification v1.1

**Status:** SPECIFICATION ONLY — **DO NOT IMPLEMENT YET**  
**Last Updated:** 2026-01-15  
**Supersedes:** N/A (new feature)  
**Related Specs:** `COMPOSERS_SUBWORKFLOWS_V2_SPEC.md`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Goals and Non-Goals](#2-goals-and-non-goals)
3. [Terminology](#3-terminology)
4. [Project Model ("Open Project")](#4-project-model-open-project)
5. [Project Config (project.json)](#5-project-config-projectjson)
6. [Context Registry (context_registry.json)](#6-context-registry-context_registryjson)
7. [ContextKey Schema (Detailed)](#7-contextkey-schema-detailed)
8. [GUI Rules: No Free-Text Keys](#8-gui-rules-no-free-text-keys)
9. [Workflow JSON Compatibility (Export/Import)](#9-workflow-json-compatibility-exportimport)
10. [Subworkflow Context Isolation: Fork + Merge (Sandboxed)](#10-subworkflow-context-isolation-fork--merge-sandboxed)
11. [Runtime Enforcement (Validated Context)](#11-runtime-enforcement-validated-context)
12. [Project-Only Libraries](#12-project-only-libraries)
13. [Error Handling & User Messages](#13-error-handling--user-messages)
14. [Migration & Adoption Plan](#14-migration--adoption-plan)
15. [Acceptance Criteria](#15-acceptance-criteria)
16. [Implementation Phases (Recommended)](#16-implementation-phases-recommended)
17. [Appendix A: Engine-Provided Keys (Reserved)](#17-appendix-a-engine-provided-keys-reserved)
18. [Appendix B: Example Registry File](#18-appendix-b-example-registry-file)
19. [Appendix C: Fork+Merge Execution Trace Example](#19-appendix-c-forkmerge-execution-trace-example)

---

## 1) Executive Summary

This specification introduces a **project-scoped Context Registry** that makes context keys in MicroC workflows:

- **Unique** (no "tizio/caio" duplication)
- **Selectable** (no free-text key entry in GUI)
- **Strictly validated** at runtime (key existence + type + write policy)
- **Immediately available** in GUI once created
- **Safe across subworkflow boundaries** (fork + merge with sandboxed visibility)

### Hard Product Decisions (Non-Negotiable)

1. **Project is the unit of context truth** — context keys live in a project registry, not in individual workflow JSONs
2. **No free-text context keys in GUI** — all key selection uses registry pickers with "Create new key…"
3. **Fork + merge at subworkflow call boundaries** — called subworkflows run on a sandboxed child context, then controlled merge back
4. **Strict import required for python types** — if a key declares a python type, runtime must import it to validate
5. **Registry edits are concurrency-safe** — all saves require matching `revision` or are rejected
6. **Project-only function libraries** — libraries stored in project config; workflow-local library lists not supported

---

## 2) Goals and Non-Goals

### 2.1 Goals (Hard Requirements)

1. **Project-scoped registry**
   - One registry shared by all workflows in a project folder (not per-workflow JSON)

2. **Strict, centralized context keys**
   - All keys used by GUI (context mapping, context read/write nodes, etc.) must come from registry

3. **No duplication**
   - Registry enforces canonical naming + uniqueness + aliasing for renames

4. **Immediate visibility**
   - Creating a key makes it instantly available in all key pickers across GUI

5. **Runtime enforcement**
   - Writes/updates to context validated against registry (key existence + type + write policy)
   - Context deletion forbidden at runtime

6. **Sandboxed subworkflow execution**
   - Child context starts empty; only explicitly mapped keys are visible
   - Changes merge back only when allowed by registry policy

### 2.2 Non-Goals (Explicitly Out of Scope for v1)

- Advanced static type inference from Python code
- Automatic discovery of outputs written by arbitrary function code
- Full "data lineage graphs" or automatic "producer/consumer" tracking
- Remote multi-user collaboration
- Deep copy of context objects (shallow copy only)

---

## 3) Terminology

| Term | Definition |
|------|------------|
| **Project Root** | Folder opened via "Open Project"; holds project config and registry |
| **Workflow File** | v2 workflow JSON as per `COMPOSERS_SUBWORKFLOWS_V2_SPEC.md` (version `"2.0"`) |
| **Execution Context** | Runtime dictionary passed between workflow functions (`context: Dict[str, Any]`) |
| **Context Registry** | Project-level database of allowed context keys (`.microc/context_registry.json`) |
| **Context Key** | Registered key entry (stable ID + canonical name + type + policy) |
| **Canonical Name** | The "one true" string name for a key (e.g., `core.population`) |
| **Alias** | Deprecated prior name that still resolves to same key ID |
| **Write Policy** | How/if a key may be set/overwritten by workflow execution |
| **Fork** | Creating a shallow copy of parent context for child subworkflow execution |
| **Merge** | Applying validated child context changes back to parent context |
| **Sandboxed Visibility** | Child context starts empty; only mapped keys are present |

---

## 4) Project Model ("Open Project")

### 4.1 "Open Project" Command (GUI)

**Menu:** `File → Open Project…`

**Flow:**
1. User selects a folder
2. GUI sets it as **active project root**
3. GUI loads (or creates) project config and registry:
   - `.microc/project.json`
   - `.microc/context_registry.json`
4. GUI refreshes:
   - Context key pickers
   - Validation rules
   - Function libraries (project-global)
   - Recent projects list

### 4.2 Project Directory Structure (Canonical)

Inside project root:
```
project_root/
├── .microc/
│   ├── project.json              # Project configuration
│   └── context_registry.json     # Context registry (single source of truth)
├── workflows/                     # (example; user-defined)
│   ├── main.json
│   └── analysis.json
└── functions/                     # (example; user-defined)
    └── custom_library.py
```

### 4.3 Project Creation Rules

**If `.microc/project.json` is missing:**
- GUI prompts: **"Create MicroC project files in this folder?"**
  - Buttons: `Create` / `Cancel`
- On `Create`:
  - Creates `.microc/` directory
  - Writes `.microc/project.json` (see §5)
  - Writes `.microc/context_registry.json` prepopulated with **engine-provided keys** (see §17)

**If `.microc/context_registry.json` is missing but `project.json` exists:**
- GUI auto-creates registry (no prompt)
- Shows non-blocking info toast: "Context registry created"

### 4.4 Project Lifetime Rules

- **Only one active project at a time**
- **Switching projects:**
  - Must close any unsaved workflow tabs OR prompt user to save/cancel
- **Closing project:**
  - `File → Close Project` clears active project state
  - Context registry unloaded
  - Function libraries cleared

---

## 5) Project Config (`.microc/project.json`)

### 5.1 Schema (v1) — Authoritative

**Required fields:**

```json
{
  "schema_version": 1,
  "project_id": "uuid-v4-string",
  "name": "My MicroC Project",
  "context_registry_path": ".microc/context_registry.json",
  "context_enforcement": "strict",
  "function_libraries": [
    "functions/custom_library.py",
    "functions/analysis_tools.py"
  ]
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `schema_version` | `int` | ✅ | — | Must be `1` |
| `project_id` | `string` | ✅ | — | UUID v4; immutable; generated on project creation |
| `name` | `string` | ✅ | — | Human-readable project name |
| `context_registry_path` | `string` | ✅ | `.microc/context_registry.json` | Relative path to registry file |
| `context_enforcement` | `"off" \| "warn" \| "strict"` | ✅ | `"strict"` | Runtime validation mode |
| `function_libraries` | `string[]` | ✅ | `[]` | Paths to function library files (relative to project root) |

### 5.2 Context Enforcement Modes (Detailed)

| Mode | Key Existence | Type Validation | Write Policy | Deletion |
|------|---------------|-----------------|--------------|----------|
| **`off`** | Not checked | Not checked | Not checked | Allowed (not recommended) |
| **`warn`** | Warn if missing | Warn if mismatch | Warn if violated | Warn (but allow) |
| **`strict`** | **Error if missing** | **Error if mismatch** | **Error if violated** | **Error (always forbidden)** |

**Recommendation:** Always use `"strict"` for new projects.

**Note on python type imports:**
- Even in `warn` mode, if a python type cannot be imported, validation cannot proceed.
- Per §7.4.3 (strict import required), python type import failures are treated as errors regardless of enforcement mode.

### 5.3 Project-Only Function Libraries (Hard Rule)

- **Source of truth:** Only `project.json:function_libraries`
- **Workflow-local libraries:** Not supported
- **Legacy workflow files:** If a workflow JSON contains `metadata.gui.function_libraries`:
  - GUI may offer one-time "Import these into project libraries" action
  - After import, workflow-local list is ignored

**Rationale:** Project is the unit of context truth; libraries are part of that context.

### 5.4 Project Config Validation (On Load)

GUI must validate:
- `schema_version == 1`
- `project_id` is valid UUID v4
- `context_registry_path` points to valid file (or can be created)
- `context_enforcement` is one of `"off"`, `"warn"`, `"strict"`
- All paths in `function_libraries` exist (or warn user)

---

## 6) Context Registry (`.microc/context_registry.json`)

### 6.1 Top-Level Schema (v1) — Authoritative

```json
{
  "schema_version": 1,
  "project_id": "uuid-v4-string",
  "revision": 42,
  "keys": [
    { /* ContextKey object */ },
    { /* ContextKey object */ }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | `int` | ✅ | Must be `1` |
| `project_id` | `string` | ✅ | Must match `project.json:project_id` |
| `revision` | `int` | ✅ | Monotonic counter; starts at `1`; incremented on every save |
| `keys` | `ContextKey[]` | ✅ | Array of registered context keys |

### 6.2 Optimistic Concurrency Control (Hard Requirement)

**Rule:** Any edit that writes `context_registry.json` MUST:

1. Include the last-seen `revision` number
2. Succeed only if current on-disk `revision` equals last-seen `revision`
3. Increment `revision` by 1 on successful write
4. Reject save if `revision` mismatch detected

**On rejection:**
- GUI must reload registry from disk
- GUI must prompt user: "Registry was modified by another process. Please re-apply your changes."
- User must manually re-apply their edit (no auto-merge)

**No last-write-wins is allowed.**

**Implementation note:**
- Use atomic file write (write to temp file, then rename)
- Read-check-write must be atomic at application level (lock or compare-and-swap pattern)

### 6.3 Registry Validation (On Load)

GUI must validate:
- `schema_version == 1`
- `project_id` matches `project.json:project_id`
- `revision >= 1`
- All `keys[].id` are unique
- All `keys[].name` are unique (case-sensitive)
- All `keys[].aliases` are unique across all keys (no overlap with names or other aliases)
- All `keys[].name` match naming pattern (see §7.2)

If validation fails:
- Show error dialog with specific issue
- Block project load until registry is manually fixed

---

## 7) ContextKey Schema (Detailed)

### 7.1 Full ContextKey Object

```json
{
  "id": "uuid-v4-string",
  "name": "core.population",
  "aliases": ["population"],
  "type": {
    "kind": "python",
    "module": "micropy.core",
    "qualname": "Population"
  },
  "write_policy": "write_once",
  "delete_policy": "forbidden",
  "description": "The main cell population object",
  "tags": ["core", "required"],
  "example": null,
  "owner": "engine",
  "visibility": "normal",
  "deprecated": false
}
```

### 7.2 Identity and Stability

| Field | Type | Required | Mutable | Description |
|-------|------|----------|---------|-------------|
| `id` | `string` | ✅ | ❌ | UUID v4; immutable forever; used for stable references |
| `name` | `string` | ✅ | ✅ | Canonical display/serialization name |
| `aliases` | `string[]` | ✅ | ✅ | Alternate names that resolve to same key (for renames/deprecation) |

**Naming rules:**
- **Pattern:** `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$`
- **Examples (valid):**
  - `population` (flat, legacy)
  - `core.population` (namespaced, recommended)
  - `analysis.metrics.score` (multi-level)
- **Examples (invalid):**
  - `Population` (uppercase)
  - `core-population` (hyphen)
  - `.population` (leading dot)
  - `population.` (trailing dot)

**Uniqueness rules:**
- `name` must be unique across all keys
- All `aliases` must be unique across all keys (no overlap with names or other aliases)
- `id` must be unique (enforced by UUID generation)

**Rename workflow:**
1. User renames key `old_name` → `new_name`
2. GUI adds `old_name` to `aliases[]`
3. GUI sets `name = new_name`
4. GUI increments `revision` and saves
5. All existing workflow JSONs continue to work (they reference by ID internally, export by name)

### 7.3 Policy Fields (Runtime-Enforced)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `write_policy` | `"read_only" \| "write_once" \| "mutable"` | ✅ | — | Controls write behavior |
| `delete_policy` | `"forbidden"` | ✅ | `"forbidden"` | v1: always forbidden |

**Write Policy Semantics:**

| Policy | Meaning | Use Case |
|--------|---------|----------|
| `read_only` | Cannot be written during execution (including merge-back) | Engine-provided inputs (e.g., `dt`, `results_dir`) |
| `write_once` | Allowed only if key not already present in target context | Initialization keys (e.g., `core.population` created once) |
| `mutable` | Overwrite allowed; type must still match | Analysis outputs, intermediate results |

**Delete Policy:**
- v1: Always `"forbidden"`
- Runtime must reject any `del context[key]` with clear error
- Future versions may add `"allowed"` or `"warn"` modes

### 7.4 Type Descriptor (Strict Import Required)

**Type is one of:**

#### 7.4.1 Primitive Type

```json
{
  "kind": "primitive",
  "name": "int" | "float" | "bool" | "string"
}
```

**Validation:**
- `isinstance(value, int)` for `"int"`
- `isinstance(value, float)` for `"float"` (also accepts `int` for numeric compatibility)
- `isinstance(value, bool)` for `"bool"`
- `isinstance(value, str)` for `"string"`

#### 7.4.2 JSON-ish Type

```json
{
  "kind": "json",
  "name": "dict" | "list" | "any"
}
```

**Validation:**
- `isinstance(value, dict)` for `"dict"`
- `isinstance(value, list)` for `"list"`
- No validation for `"any"` (accepts anything)

#### 7.4.3 Python Type (Strict Import Required)

```json
{
  "kind": "python",
  "module": "micropy.core",
  "qualname": "Population"
}
```

**Validation:**
1. Import module: `import micropy.core`
2. Resolve qualname: `getattr(micropy.core, "Population")`
3. Check instance: `isinstance(value, Population)`

**Strict Import Requirement (Hard Rule):**

- **Before first node executes** (or at project open), runtime must validate:
  - All `type.kind="python"` keys can be imported and resolved
- **If import/resolve fails:**
  - `context_enforcement="strict"`: **Block run** with error: `"Cannot import type for key 'core.population': module 'micropy.core' not found"`
  - `context_enforcement="warn"`: **Still block** (cannot validate without import)
  - `context_enforcement="off"`: May allow execution (no validation)

**Rationale:** Python types are a strong contract. If you declare it, the environment must support it. No "best effort" fallback.

### 7.5 Documentation + UI Fields (Non-Runtime)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `description` | `string` | ❌ | `""` | Human-readable description (shown in tooltips, docs) |
| `tags` | `string[]` | ❌ | `[]` | Searchable tags (e.g., `["core", "required"]`) |
| `example` | `any` | ❌ | `null` | JSON-serializable example value (for docs/tooltips) |
| `owner` | `"engine" \| "user" \| "library"` | ❌ | `"user"` | Who created/owns this key |
| `visibility` | `"normal" \| "advanced" \| "hidden"` | ❌ | `"normal"` | UI visibility level |
| `deprecated` | `boolean` | ❌ | `false` | If true, show deprecation warning in GUI |

**UI behavior:**
- `visibility="hidden"`: Don't show in pickers unless "Show hidden keys" enabled
- `visibility="advanced"`: Show only in "Advanced mode" or with filter
- `deprecated=true`: Show with strikethrough + warning icon; suggest replacement in tooltip

---

## 8) GUI Rules: No Free-Text Keys

### 8.1 Context Registry Panel (Project-Global)

**Location:** Sidebar or dedicated panel (e.g., "Context Registry" tab)

**Must support:**
- **Create key** (with full form: name, type, policy, description, etc.)
- **Edit key** (change description, tags, visibility, deprecation status)
- **Rename key** (adds old name to aliases)
- **Deprecate key** (sets `deprecated=true`, prompts for replacement suggestion)
- **Find usages** (search all open workflows for references to this key)
- **Validate registry** (check for duplicate names, invalid patterns, missing python imports)
- **Export registry** (for documentation or sharing)

**UI requirements:**
- Show all keys in searchable/filterable list
- Group by namespace (e.g., `core.*`, `analysis.*`)
- Show type, policy, owner, visibility badges
- Highlight deprecated keys
- Show usage count (if available)

### 8.2 Key Selection Everywhere Uses Registry Pickers

**Affected UI components:**
- SubWorkflowCall node: `context_mapping` source/target selectors
- Context read/write nodes (if any)
- Function parameter binding (if context keys are used)
- Any other place where a context key can be referenced

**Picker behavior:**
- **Search existing keys** (by name, alias, tags, description)
- **Filter by type** (e.g., show only `python` types)
- **Filter by visibility** (normal/advanced/hidden)
- **"Create new key…"** button at bottom of picker

**No free-text input allowed.**

### 8.3 "Create Key…" from Pickers (Immediate Availability)

**Flow:**
1. User clicks "Create new key…" in picker
2. GUI shows "Create Context Key" dialog:
   - Name (validated against pattern)
   - Type (dropdown: primitive/json/python)
   - Write policy (dropdown: read_only/write_once/mutable)
   - Description (optional)
   - Tags (optional)
3. User clicks "Create"
4. GUI validates:
   - Name is unique
   - Name matches pattern
   - Python type can be imported (if applicable)
5. GUI writes to registry (with revision check)
6. GUI refreshes all pickers
7. **New key is immediately available** in all pickers across all open workflows

**Error handling:**
- If revision mismatch: reload registry, prompt user to retry
- If name conflict: show error, suggest alternative name
- If python type import fails: show error, suggest checking module path

### 8.4 Validation on Workflow Save/Export

**Before save/export:**
- GUI validates all context key references resolve to registry entries
- If any key is missing or deprecated:
  - Show warning dialog listing issues
  - Allow user to fix or proceed anyway (with warning marker on workflow)

**On export:**
- Convert all key IDs to canonical names (see §9.3)

---

## 9) Workflow JSON Compatibility (Export/Import)

### 9.1 Why ID-vs-Name Duality

**Problem:**
- Runtime schema stores `context_mapping` as strings: `{ [from: string]: string }`
- GUI must be stable under rename (if key renamed, workflows shouldn't break)

**Solution:**
- GUI stores `context_mapping` internally as `{ fromKeyId: toKeyId }`
- Export converts IDs → canonical names
- Import converts names → IDs

### 9.2 Internal GUI Storage (In-Memory)

**GUI representation of SubWorkflowCall:**

```typescript
interface SubWorkflowCallNode {
  id: string;
  type: "SubWorkflowCall";
  subworkflow_path: string;
  context_mapping: {
    [fromKeyId: string]: toKeyId: string;
  };
  // ... other fields
}
```

**Example:**
```json
{
  "context_mapping": {
    "a1b2c3d4-uuid": "e5f6g7h8-uuid"
  }
}
```

### 9.3 Export Rule (IDs → Names)

**When exporting workflow to JSON:**

1. For each `context_mapping` entry `{ fromKeyId: toKeyId }`:
   - Resolve `fromKeyId` → `fromName` (canonical name from registry)
   - Resolve `toKeyId` → `toName` (canonical name from registry)
   - Write `{ "<fromName>": "<toName>" }`

2. If any key ID cannot be resolved:
   - Show error: "Cannot export: key ID `<id>` not found in registry"
   - Block export until fixed

**Exported JSON:**
```json
{
  "context_mapping": {
    "core.population": "analysis.population"
  }
}
```

### 9.4 Import Rule (Names → IDs)

**When importing workflow from JSON:**

1. For each `context_mapping` entry `{ "<fromName>": "<toName>" }`:
   - Resolve `fromName` by:
     - Exact match on canonical `name`
     - Match on `aliases`
   - Resolve `toName` similarly
   - Store internally as `{ fromKeyId: toKeyId }`

2. If any name cannot be resolved:
   - Mark node as invalid
   - Show error in GUI: "Unknown context key: `<name>`"
   - Require user to fix before run/export

**Resolution priority:**
1. Exact match on `name`
2. Match on `aliases` (if multiple matches, prefer non-deprecated)
3. If no match: error

### 9.5 Legacy Workflow Support

**If workflow JSON contains `metadata.gui.function_libraries`:**
- GUI shows one-time prompt: "Import these libraries into project config?"
  - `Import` → add to `project.json:function_libraries`, remove from workflow JSON
  - `Ignore` → workflow-local list is ignored going forward

**If workflow JSON contains free-text context keys (pre-registry):**
- GUI attempts to auto-match to registry keys by name
- If no match: prompt user to create or map to existing key

---

## 10) Subworkflow Context Isolation: Fork + Merge (Sandboxed)

### 10.1 Overview: Sandboxed Visibility (Hard Rule)

**Decision:** Child context starts **empty**; only explicitly mapped keys are visible.

**Rationale:**
- Maximum safety: child cannot accidentally read/write parent keys
- Explicit contract: `context_mapping` defines the complete interface
- Predictable merge: only mapped keys can be modified

**Contrast with "same dict" or "fork all keys":**
- Same dict: child sees everything, writes leak immediately (rejected)
- Fork all keys: child sees everything, merge is complex (rejected)
- **Sandboxed (chosen):** child sees only mapped keys, merge is simple and safe

### 10.2 Call Execution Phases (Detailed)

For a subworkflow call `A → B` with `context_mapping`:

```
Phase 1: Snapshot parent context
Phase 2: Create empty child context
Phase 3: Apply context_mapping into child (validated writes)
Phase 4: Execute subworkflow B using child context
Phase 5: Compute delta (which keys were added/modified in child)
Phase 6: Validate delta against registry
Phase 7: Merge delta into parent (validated writes)
Phase 8: Return updated parent context
```

### 10.3 Phase 1: Snapshot Parent Context

**Purpose:** Preserve parent state for delta computation and rollback.

**Implementation:**
- Create shallow copy of parent dict: `parent_snapshot = dict(parent_context)`
- Store snapshot for later comparison

**Note:** Shallow copy means object references are shared. If child modifies a mutable object (e.g., appends to a list), parent sees it. This is acceptable and expected (deep copy is too expensive and often wrong).

### 10.4 Phase 2: Create Empty Child Context

**Purpose:** Start with clean slate for sandboxed execution.

**Implementation:**
- `child_context = {}` (empty dict)
- No keys from parent are copied (except via mapping in Phase 3)

### 10.5 Phase 3: Apply context_mapping into Child (Validated Writes)

**Purpose:** Populate child with only the keys specified in `context_mapping`.

**For each mapping entry `from → to`:**

1. **Resolve key IDs to canonical names** (already done during import/load)
2. **Check source key exists in parent:**
   - If `from` missing in parent:
     - `context_enforcement="strict"`: **Fail call** with error: `"Missing required mapping source: '<from_name>'"`
     - `context_enforcement="warn"`: Log warning, skip this mapping entry
     - `context_enforcement="off"`: Skip silently
3. **Validate target key against registry:**
   - Resolve `to` key in registry
   - Validate type of `parent[from]` matches `to` key type
   - Validate `to` key write policy allows write into empty child (always allowed for `write_once` and `mutable`, forbidden for `read_only`)
4. **Write to child:**
   - `child_context[to] = parent[from]`

**Example:**

Parent context:
```python
{
  "core.population": <Population object>,
  "core.dt": 0.1
}
```

Mapping:
```json
{
  "core.population": "analysis.population",
  "core.dt": "dt"
}
```

Child context after Phase 3:
```python
{
  "analysis.population": <Population object>,  # same reference as parent
  "dt": 0.1
}
```

**Important:** Child does NOT have `core.population` or `core.dt` keys. It only has the mapped keys.

### 10.6 Phase 4: Execute Subworkflow B Using Child Context

**Purpose:** Run the called subworkflow with sandboxed context.

**Implementation:**
- Execute subworkflow B's nodes in order
- All context reads/writes operate on `child_context`
- Any writes must be validated against registry (see §11)

**Example writes during execution:**

```python
# Inside a function node in subworkflow B:
context["analysis.score"] = 0.91  # validated write (must be in registry)
context["analysis.population"].update()  # modifies object in-place (allowed)
```

Child context after Phase 4:
```python
{
  "analysis.population": <Population object>,  # possibly modified
  "dt": 0.1,
  "analysis.score": 0.91  # newly added
}
```

### 10.7 Phase 5: Compute Delta

**Purpose:** Identify which keys were added or modified in child.

**Implementation:**

1. **Added keys:** Keys in `child_context` but not in initial child (after Phase 3)
2. **Modified keys:** Keys in both, but value changed (identity check: `child[k] is not initial[k]`)

**Delta representation:**

```python
delta = {
  "added": ["analysis.score"],
  "modified": ["analysis.population"]  # if object reference changed
}
```

**Note:** We track which keys were touched, not deep object changes. If a function modifies a list in-place, we may not detect it unless the reference changed. This is acceptable (deep diff is too expensive).

**Alternative implementation (simpler but less precise):**
- Track all writes via a `ValidatedContext` wrapper that records touched keys
- Delta = set of all written keys

### 10.8 Phase 6: Validate Delta Against Registry

**Purpose:** Ensure all child writes are allowed before merging back.

**For each key in delta:**

1. **Validate key is registered:**
   - Resolve key name (canonical or alias) in registry
   - If not found:
     - `context_enforcement="strict"`: **Fail merge** with error: `"Unknown context key written: '<key_name>'"`
     - `context_enforcement="warn"`: Log warning, skip this key in merge
     - `context_enforcement="off"`: Allow (no validation)

2. **Validate python type imports** (if `kind="python"`):
   - Ensure type can be imported (already checked at project load, but re-check for safety)
   - If import fails: treat as error (per §7.4.3 strict import requirement)

3. **Validate type matches:**
   - Check `isinstance(child[key], expected_type)`
   - If mismatch:
     - `context_enforcement="strict"`: **Fail merge** with error: `"Type mismatch for key '<key_name>': expected <type>, got <actual_type>"`
     - `context_enforcement="warn"`: Log warning, skip this key in merge
     - `context_enforcement="off"`: Allow

4. **Validate write policy against parent** (merge target):
   - `read_only`: **Always reject** (cannot merge back)
   - `write_once`: Allow only if key not already in parent
   - `mutable`: Allow overwrite

**If any validation fails in strict mode:**
- Abort merge
- Rollback parent context to snapshot (if needed)
- Fail the call with detailed error message

### 10.9 Phase 7: Merge Delta into Parent (Validated Writes)

**Purpose:** Apply validated child changes back to parent.

**For each key in validated delta:**

1. **Check write policy one more time** (defensive):
   - `read_only`: Skip (should have been caught in Phase 6)
   - `write_once`: Write only if `key not in parent_context`
   - `mutable`: Overwrite

2. **Write to parent:**
   - `parent_context[key] = child_context[key]`

**Example:**

Parent context before merge:
```python
{
  "core.population": <Population object>,
  "core.dt": 0.1
}
```

Delta to merge:
```python
{
  "analysis.score": 0.91
}
```

Parent context after merge:
```python
{
  "core.population": <Population object>,
  "core.dt": 0.1,
  "analysis.score": 0.91  # merged from child
}
```

**Important:** Only keys in delta are merged. Keys that were mapped but not modified in child are NOT re-written to parent (no-op).

### 10.10 Phase 8: Return Updated Parent Context

**Purpose:** Continue execution with merged context.

**Implementation:**
- Return `parent_context` (now updated with child changes)
- Discard `child_context` and snapshot

### 10.11 Conflict Resolution (Explicit Rules)

**Scenario:** Child writes to key `k`, parent also has key `k`.

**Resolution:**
- If `k` has `write_policy="mutable"`: Child wins (overwrite allowed)
- If `k` has `write_policy="write_once"`: Merge rejected (key already exists in parent)
- If `k` has `write_policy="read_only"`: Merge rejected (cannot write)

**No silent conflict resolution.** All conflicts are explicit errors in strict mode.

### 10.12 Failure Semantics

**If any phase fails:**

- **Phase 3 (mapping application):** Fail call immediately, parent context unchanged
- **Phase 4 (subworkflow execution):** Fail call, parent context unchanged (child changes discarded)
- **Phase 6 (delta validation):** Fail call, parent context unchanged (rollback to snapshot if needed)
- **Phase 7 (merge):** Should not fail if Phase 6 succeeded (defensive checks only)

**In all cases:**
- Parent context is never partially mutated
- Error message includes:
  - Which phase failed
  - Which key caused the failure
  - What the violation was (missing key, type mismatch, policy violation)

### 10.13 Reserved Execution Keys (Engine-Provided)

**Per v2 spec, runtime provides:**
- `subworkflow_name` (string)
- `subworkflow_kind` (string)
- `results_dir` (string)
- `subworkflow_results_dir` (string)

**Registry treatment:**
- These keys must be in registry with `owner="engine"` and `write_policy="read_only"`
- Runtime injects them into child context **after** Phase 3 (so they're always available)
- They are NOT part of `context_mapping` (implicit, not explicit)

**Alternative (simpler):**
- Treat these as "magic" keys that bypass registry validation
- Document them clearly as engine-provided

**Recommendation:** Register them explicitly for consistency, but mark as `visibility="hidden"` so users don't see them in pickers.

---

## 11) Runtime Enforcement (Validated Context)

### 11.1 What "Enforcement" Covers

Runtime must enforce registry rules for:

1. **Any `context[k] = v` write** (including within functions and within merge)
2. **Any attempt to delete** (`del context[k]`) → always error in strict mode
3. **Function return contract** (see §11.3)
4. **Optional: Function input injection checks** (if function metadata says it needs `x`, and `x` missing)

### 11.2 Validated Write Implementation (Conceptual)

**Wrapper class (conceptual, not required implementation):**

```python
class ValidatedContext:
    def __init__(self, data: dict, registry: ContextRegistry, enforcement: str):
        self._data = data
        self._registry = registry
        self._enforcement = enforcement
        self._touched_keys = set()

    def __setitem__(self, key: str, value: Any):
        # 1. Resolve key in registry
        key_def = self._registry.resolve(key)
        if not key_def:
            if self._enforcement == "strict":
                raise KeyError(f"Unknown context key: '{key}'")
            elif self._enforcement == "warn":
                warnings.warn(f"Unknown context key: '{key}'")
            # off: allow

        # 2. Validate type
        if key_def and not self._validate_type(value, key_def.type):
            if self._enforcement == "strict":
                raise TypeError(f"Type mismatch for key '{key}'")
            elif self._enforcement == "warn":
                warnings.warn(f"Type mismatch for key '{key}'")

        # 3. Validate write policy
        if key_def:
            if key_def.write_policy == "read_only":
                if self._enforcement == "strict":
                    raise PermissionError(f"Cannot write to read-only key '{key}'")
            elif key_def.write_policy == "write_once":
                if key in self._data:
                    if self._enforcement == "strict":
                        raise PermissionError(f"Cannot overwrite write-once key '{key}'")

        # 4. Perform write
        self._data[key] = value
        self._touched_keys.add(key)

    def __delitem__(self, key: str):
        if self._enforcement == "strict":
            raise PermissionError(f"Context key deletion is forbidden: '{key}'")
        elif self._enforcement == "warn":
            warnings.warn(f"Context key deletion is forbidden: '{key}'")
        # off: allow (not recommended)
        del self._data[key]
```

**Note:** Actual implementation may use a different approach (e.g., validation hooks, decorators, etc.). This is illustrative only.

### 11.3 Function Return Contract (To Avoid Implicit Keys)

**Problem:** If functions return arbitrary values, runtime might create implicit keys not in registry.

**Solution (Hard Rule):**

Workflow functions may return:
- `None` (no context updates)
- `Dict[str, Any]` (context updates, each key validated)

**Returning any other type is an error in strict mode.**

**Example (allowed):**

```python
def my_function(context):
    # ... do work ...
    return {"analysis.score": 0.91}  # validated write
```

**Example (allowed):**

```python
def my_function(context):
    # ... do work ...
    return None  # no updates
```

**Example (forbidden in strict mode):**

```python
def my_function(context):
    return 42  # error: expected None or dict
```

**Runtime behavior:**
- If function returns dict:
  - For each `k, v` in dict: validate and write `context[k] = v`
- If function returns None:
  - No context updates
- If function returns anything else:
  - `context_enforcement="strict"`: Fail with error
  - `context_enforcement="warn"`: Log warning, ignore return value
  - `context_enforcement="off"`: Ignore return value

### 11.4 Strict Import Required Enforcement Point

**When:** Before first node executes (or at project open).

**What:** Validate all `type.kind="python"` keys can be imported and resolved.

**How:**

```python
for key in registry.keys:
    if key.type.kind == "python":
        try:
            module = importlib.import_module(key.type.module)
            cls = getattr(module, key.type.qualname)
        except (ImportError, AttributeError) as e:
            if enforcement == "strict" or enforcement == "warn":
                raise RuntimeError(
                    f"Cannot import type for key '{key.name}': "
                    f"module '{key.type.module}', qualname '{key.type.qualname}' - {e}"
                )
            # off: allow (no validation)
```

**Error message example:**

```
Cannot import type for key 'core.population':
module 'micropy.core', qualname 'Population' - No module named 'micropy.core'

Please ensure the required package is installed or update the key type definition.
```

### 11.5 Deletion Enforcement

**Rule:** Context key deletion is forbidden in v1.

**Implementation:**

```python
def __delitem__(self, key: str):
    if enforcement == "strict":
        raise PermissionError(
            f"Context key deletion is forbidden: '{key}'\n"
            f"Use write_policy='mutable' to overwrite instead."
        )
    elif enforcement == "warn":
        warnings.warn(f"Context key deletion is forbidden: '{key}'")
    # off: allow (not recommended)
```

---

## 12) Project-Only Libraries

### 12.1 Source of Truth

**Only:** `.microc/project.json:function_libraries`

**Not supported:**
- Workflow-local library lists in `workflow.metadata.gui.function_libraries`

### 12.2 Library Loading Behavior

**On project open:**
1. GUI reads `project.json:function_libraries`
2. GUI loads all specified library files (relative to project root)
3. GUI populates function palette with all discovered functions
4. All workflows in project see the same palette

**On workflow open (within project):**
- Workflow does NOT specify its own libraries
- Workflow uses project-global palette

### 12.3 Export/Import Behavior

**Export:**
- Exported workflow JSON does NOT include `metadata.gui.function_libraries`
- Libraries are assumed to be part of the project context

**Import:**
- If imported workflow JSON contains `metadata.gui.function_libraries`:
  - GUI shows one-time prompt: "Import these libraries into project config?"
    - `Import` → add to `project.json:function_libraries`, save project config
    - `Ignore` → workflow-local list is ignored
  - After import, remove `metadata.gui.function_libraries` from workflow JSON (or mark as ignored)

### 12.4 Conflict Resolution

**Scenario:** Two libraries define functions with the same name.

**Resolution (same as v2 spec):**
- Last library in `function_libraries` list wins (overwrite)
- OR: Use variant naming (e.g., `function_name_v2`)
- OR: Show conflict warning in GUI, require user to resolve

**Recommendation:** Use namespaced function names (e.g., `analysis.compute_score`) to avoid conflicts.

### 12.5 Library Editing Workflow

**To add a library:**
1. User opens project settings (e.g., `File → Project Settings`)
2. User adds library path to `function_libraries` list
3. GUI saves `project.json`
4. GUI reloads libraries and refreshes palette

**To remove a library:**
1. User removes library path from `function_libraries` list
2. GUI warns if any open workflows use functions from this library
3. User confirms or cancels
4. GUI saves `project.json` and refreshes palette

---

## 13) Error Handling & User Messages

### 13.1 Error Message Principles

1. **Be specific:** Include key name, expected type, actual type, policy violated
2. **Be actionable:** Suggest how to fix (e.g., "Update key type in registry" or "Change write_policy to 'mutable'")
3. **Be consistent:** Use same format for similar errors
4. **Be concise:** Don't overwhelm with technical details (but include them in logs)

### 13.2 Common Error Scenarios

#### 13.2.1 Missing Context Key (Strict Mode)

**Scenario:** Function tries to write to key not in registry.

**Error message:**
```
Context Validation Error

Unknown context key: 'analysis.new_metric'

This key is not registered in the project context registry.

Actions:
• Create this key in the Context Registry panel
• Check for typos in the key name
• Verify the key was not renamed or removed

Location: SubWorkflowCall "Run Analysis" → Function "compute_metrics"
```

#### 13.2.2 Type Mismatch

**Scenario:** Function writes wrong type to key.

**Error message:**
```
Context Validation Error

Type mismatch for key 'core.population'

Expected: micropy.core.Population
Got: dict

Actions:
• Update the function to return the correct type
• Change the key type definition in the registry if this is intentional

Location: SubWorkflowCall "Initialize" → Function "create_population"
```

#### 13.2.3 Write Policy Violation (read_only)

**Scenario:** Function tries to write to read-only key.

**Error message:**
```
Context Validation Error

Cannot write to read-only key 'core.dt'

This key is marked as read-only in the registry.

Actions:
• Remove the write to this key from your function
• Change write_policy to 'mutable' in the registry if this is intentional

Location: SubWorkflowCall "Update" → Function "modify_timestep"
```

#### 13.2.4 Write Policy Violation (write_once)

**Scenario:** Function tries to overwrite write-once key.

**Error message:**
```
Context Validation Error

Cannot overwrite write-once key 'core.population'

This key already exists and is marked as write-once.

Actions:
• Use a different key name for this output
• Change write_policy to 'mutable' in the registry if overwrites are allowed

Location: SubWorkflowCall "Reinitialize" → Function "create_population"
```

#### 13.2.5 Python Type Import Failure

**Scenario:** Registry key references python type that cannot be imported.

**Error message:**
```
Context Registry Error

Cannot import type for key 'core.population'

Module: micropy.core
Class: Population
Error: No module named 'micropy.core'

Actions:
• Install the required package: pip install micropy
• Update the key type definition if the module path changed
• Change the key type to 'json' or 'any' if strict typing is not needed

This error must be resolved before running any workflows.
```

#### 13.2.6 Registry Revision Conflict

**Scenario:** User tries to save registry, but another process modified it.

**Error message:**
```
Registry Save Conflict

The context registry was modified by another process.

Your changes have NOT been saved.

Actions:
• Click "Reload" to see the latest registry
• Re-apply your changes manually
• Check if another instance of the application is open

[Reload Registry] [Cancel]
```

#### 13.2.7 Missing Mapping Source

**Scenario:** Subworkflow call maps from key that doesn't exist in parent.

**Error message:**
```
Context Mapping Error

Missing required mapping source: 'core.population'

The parent context does not contain this key.

Actions:
• Ensure the parent workflow creates this key before calling this subworkflow
• Remove this mapping if it's not required
• Check for typos in the key name

Location: SubWorkflowCall "Run Analysis"
Mapping: core.population → analysis.population
```

### 13.3 Warning Messages (Warn Mode)

**Format:** Non-blocking toast or console warning.

**Example:**
```
⚠️ Context Warning: Unknown key 'analysis.temp_result' written by function 'compute_metrics'
```

### 13.4 Info Messages

**Example (registry auto-created):**
```
ℹ️ Context registry created at .microc/context_registry.json
```

**Example (key deprecated):**
```
⚠️ Key 'population' is deprecated. Use 'core.population' instead.
```

---

## 14) Migration & Adoption Plan

### 14.1 Existing Projects (No Registry)

**Scenario:** User opens a folder with existing workflow JSONs but no `.microc/` directory.

**Flow:**
1. GUI detects no project config
2. GUI prompts: "Create MicroC project files in this folder?"
3. On `Create`:
   - Create `.microc/project.json` with default settings
   - Create `.microc/context_registry.json` with engine-provided keys
   - Scan all workflow JSONs for context keys
   - Prompt: "Import discovered context keys into registry?"
     - Show list of discovered keys (from context_mapping, function returns, etc.)
     - User can review, edit types/policies, then import
   - Save registry

### 14.2 Existing Workflows (Free-Text Keys)

**Scenario:** Workflow JSON contains context keys as free-text strings (pre-registry).

**Flow:**
1. GUI imports workflow
2. For each context key reference:
   - Try to resolve in registry (by name or alias)
   - If not found:
     - Mark node as invalid
     - Show warning: "Unknown context key: '<key_name>'"
     - Offer "Create in registry" button
3. User creates missing keys or maps to existing keys
4. GUI re-validates workflow

### 14.3 Gradual Adoption (Mixed Mode)

**Scenario:** Team wants to adopt registry gradually.

**Recommendation:**
1. Start with `context_enforcement="warn"` (non-blocking)
2. Create registry with known keys
3. Run workflows, collect warnings
4. Add missing keys to registry
5. Switch to `context_enforcement="strict"` when ready

### 14.4 Backward Compatibility

**Goal:** Existing v2 workflows should continue to work (with warnings).

**Guarantees:**
- Workflow JSON schema unchanged (still v2)
- Runtime context dict unchanged (`Dict[str, Any]`)
- Function signatures unchanged

**Changes:**
- Context writes are validated (can be disabled with `enforcement="off"`)
- Context keys must be in registry (can be auto-created)
- Libraries are project-global (workflow-local lists ignored)

---

## 15) Acceptance Criteria

### 15.1 Fork + Merge Correctness

- [ ] Changes performed inside a called subworkflow are not visible to caller until merge-back
- [ ] If subworkflow call fails, caller context is not partially mutated
- [ ] Child context starts empty (sandboxed visibility)
- [ ] Only mapped keys are visible in child
- [ ] Merge applies only validated delta

### 15.2 Strict Python Type Import

- [ ] If any python type in registry cannot be imported/resolved, run is blocked with clear error
- [ ] No "best effort" fallback for python type keys
- [ ] Error message includes module, qualname, and import error details

### 15.3 Optimistic Concurrency

- [ ] Two registry edits cannot silently overwrite each other
- [ ] Stale save attempt is rejected due to revision mismatch
- [ ] User is prompted to reload and re-apply changes

### 15.4 Project-Only Libraries

- [ ] Opening a project defines palette libraries for all workflows
- [ ] Workflow-local libraries are ignored/not supported
- [ ] Legacy workflow libraries can be imported into project config

### 15.5 No Free-Text Keys in GUI

- [ ] All context key selection uses registry pickers
- [ ] "Create new key…" is available in all pickers
- [ ] Created keys are immediately available in all pickers
- [ ] No text input fields for context key names (except in "Create key" dialog)

### 15.6 Registry Validation

- [ ] Duplicate names are rejected
- [ ] Invalid naming patterns are rejected
- [ ] Python type imports are validated on project load
- [ ] Alias conflicts are detected

### 15.7 Export/Import Stability

- [ ] Exported workflows use canonical key names
- [ ] Imported workflows resolve names to IDs correctly
- [ ] Renamed keys (via aliases) are resolved correctly
- [ ] Missing keys are flagged with actionable errors

### 15.8 Runtime Enforcement

- [ ] Writes to unknown keys are rejected (strict mode)
- [ ] Type mismatches are rejected (strict mode)
- [ ] Write policy violations are rejected (strict mode)
- [ ] Deletion attempts are rejected (strict mode)
- [ ] Function return contract is enforced (strict mode)

---

## 16) Implementation Phases (Recommended)

### Phase 1: Project Model + Registry (No Runtime Enforcement)

**Goal:** Get project structure and registry working in GUI.

**Tasks:**
- Implement "Open Project" command
- Implement project config loading/saving
- Implement registry loading/saving with revision checks
- Implement Context Registry panel (create/edit/rename/deprecate keys)
- Implement registry pickers in GUI (replace free-text inputs)
- Implement "Create key…" from pickers

**Acceptance:**
- Can create project
- Can create/edit keys in registry
- Can select keys from pickers
- Registry saves with revision checks

### Phase 2: Export/Import (ID ↔ Name Conversion)

**Goal:** Make workflows stable under key renames.

**Tasks:**
- Implement internal GUI storage (IDs)
- Implement export (IDs → names)
- Implement import (names → IDs)
- Implement alias resolution

**Acceptance:**
- Exported workflows use canonical names
- Imported workflows resolve to IDs
- Renamed keys work correctly

### Phase 3: Runtime Enforcement (Validated Context)

**Goal:** Enforce registry rules at runtime.

**Tasks:**
- Implement ValidatedContext wrapper (or equivalent)
- Implement write validation (key existence, type, policy)
- Implement deletion prevention
- Implement function return contract validation
- Implement python type import validation

**Acceptance:**
- Writes to unknown keys are rejected (strict mode)
- Type mismatches are rejected (strict mode)
- Write policy violations are rejected (strict mode)

### Phase 4: Fork + Merge (Sandboxed Subworkflows)

**Goal:** Implement safe subworkflow context isolation.

**Tasks:**
- Implement child context creation (empty)
- Implement context_mapping application (validated writes)
- Implement delta computation
- Implement delta validation
- Implement merge-back (validated writes)
- Implement failure rollback

**Acceptance:**
- Child context starts empty
- Only mapped keys are visible in child
- Merge applies only validated delta
- Failures don't mutate parent

### Phase 5: Project-Only Libraries

**Goal:** Move libraries to project config.

**Tasks:**
- Implement library loading from project config
- Implement library editing in project settings
- Implement legacy library import from workflows
- Remove workflow-local library support

**Acceptance:**
- Libraries loaded from project config
- All workflows see same palette
- Legacy workflows can import libraries

### Phase 6: Polish + Migration Tools

**Goal:** Make adoption smooth.

**Tasks:**
- Implement auto-discovery of keys from existing workflows
- Implement bulk key import
- Implement validation reports
- Implement migration guide/wizard
- Improve error messages

**Acceptance:**
- Existing projects can be migrated easily
- Clear error messages guide users
- Validation reports help find issues

---

## 17) Appendix A: Engine-Provided Keys (Reserved)

**These keys must be prepopulated in every new registry:**

| Key Name | Type | Write Policy | Description |
|----------|------|--------------|-------------|
| `dt` | `primitive:float` | `read_only` | Simulation timestep |
| `results_dir` | `primitive:string` | `read_only` | Top-level results directory |
| `subworkflow_name` | `primitive:string` | `read_only` | Current subworkflow name |
| `subworkflow_kind` | `primitive:string` | `read_only` | Current subworkflow kind |
| `subworkflow_results_dir` | `primitive:string` | `read_only` | Current subworkflow results directory |

**Additional recommended keys (project-specific):**

| Key Name | Type | Write Policy | Description |
|----------|------|--------------|-------------|
| `core.population` | `python:micropy.core.Population` | `write_once` | Main cell population |
| `core.simulator` | `python:micropy.core.Simulator` | `write_once` | Simulation engine |

**Note:** Projects may add their own keys. These are just examples.

---

## 18) Appendix B: Example Registry File

```json
{
  "schema_version": 1,
  "project_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "revision": 5,
  "keys": [
    {
      "id": "00000000-0000-0000-0000-000000000001",
      "name": "dt",
      "aliases": [],
      "type": {
        "kind": "primitive",
        "name": "float"
      },
      "write_policy": "read_only",
      "delete_policy": "forbidden",
      "description": "Simulation timestep",
      "tags": ["engine", "core"],
      "example": 0.1,
      "owner": "engine",
      "visibility": "normal",
      "deprecated": false
    },
    {
      "id": "00000000-0000-0000-0000-000000000002",
      "name": "core.population",
      "aliases": ["population"],
      "type": {
        "kind": "python",
        "module": "micropy.core",
        "qualname": "Population"
      },
      "write_policy": "write_once",
      "delete_policy": "forbidden",
      "description": "Main cell population object",
      "tags": ["core", "required"],
      "example": null,
      "owner": "engine",
      "visibility": "normal",
      "deprecated": false
    },
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567891",
      "name": "analysis.metrics",
      "aliases": [],
      "type": {
        "kind": "json",
        "name": "dict"
      },
      "write_policy": "mutable",
      "delete_policy": "forbidden",
      "description": "Analysis metrics and scores",
      "tags": ["analysis", "output"],
      "example": {"score": 0.91, "count": 42},
      "owner": "user",
      "visibility": "normal",
      "deprecated": false
    }
  ]
}
```

---

## 19) Appendix C: Fork+Merge Execution Trace Example

**Scenario:**
- Parent workflow calls subworkflow "Run Analysis"
- Mapping: `core.population → analysis.population`
- Subworkflow writes `analysis.score`

**Trace:**

```
=== Phase 1: Snapshot Parent ===
parent_snapshot = {
  "core.population": <Population@0x123>,
  "dt": 0.1
}

=== Phase 2: Create Empty Child ===
child_context = {}

=== Phase 3: Apply Mapping ===
Mapping: core.population → analysis.population
  Source exists: ✓
  Target key valid: ✓
  Type matches: ✓
  Write policy allows: ✓
  Write: child_context["analysis.population"] = <Population@0x123>

child_context = {
  "analysis.population": <Population@0x123>
}

=== Phase 4: Execute Subworkflow ===
Function "compute_score" executes:
  Reads: child_context["analysis.population"]
  Writes: child_context["analysis.score"] = 0.91

child_context = {
  "analysis.population": <Population@0x123>,
  "analysis.score": 0.91
}

=== Phase 5: Compute Delta ===
delta = {
  "added": ["analysis.score"],
  "modified": []
}

=== Phase 6: Validate Delta ===
Key "analysis.score":
  Registered: ✓
  Type matches: ✓ (float)
  Write policy: mutable ✓
  Can merge: ✓

=== Phase 7: Merge Delta ===
parent_context["analysis.score"] = 0.91

parent_context = {
  "core.population": <Population@0x123>,
  "dt": 0.1,
  "analysis.score": 0.91
}

=== Phase 8: Return ===
Return parent_context (updated)
```

---

## End of Specification

**Next Steps:**
1. Review this spec with team
2. Confirm all design decisions
3. Begin implementation (Phase 1 recommended)
4. Iterate based on feedback

**Questions? Clarifications?**
- Contact: [Your team/email]
- Related docs: `COMPOSERS_SUBWORKFLOWS_V2_SPEC.md`





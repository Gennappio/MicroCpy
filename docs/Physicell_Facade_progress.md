# PhysiCell Black-Box Facade — Phase 0 & Phase 1 Reference

Companion to `Physicell_Facade_plan.md` (architecture/intent) and the
implementation plan at
`~/.claude/plans/look-at-the-file-sprightly-dragon.md`.

This document covers **what was actually built** in Phases 0 and 1, where
the code lives, the contracts it exposes, and how to test / poke at it.

## Status

| Phase | Status | Outcome |
|---|---|---|
| 0 — Cleanup | ✅ Done | Old pybind11 / per-cell-MaBoSS Python adapter removed |
| 1 — Observability runtime | ✅ Done | `occ_observability.{h,cpp}` ships, validated |
| 2 — Project scaffold codegen | ⏳ Next | XML / Makefile / custom.cpp generation |
| 3 — Hill-rules CSV + grammar (MVP) | — | |
| 4 — Run driver + GUI integration | — | |
| 5 — Fragment library | — | Deferred |

---

## Phase 0 — Cleanup

The earlier `PHYSICELL_PORT.md` direction proposed wrapping PhysiCell
kernels via pybind11. The new facade plan supersedes it, so the dead
code was removed before Phase 1 started.

### What was deleted

**Adapter trees** (the old pybind11 surface):

```
opencellcomms_engine/src/adapters/physicell_mechanics/   # incl. compiled .so
opencellcomms_engine/src/adapters/physiboss/             # config_loader, coupling, …
```

**Workflow functions** that transitively depended on those adapters:

```
src/workflow/functions/initialization/setup_physiboss_model.py
src/workflow/functions/initialization/physiboss_treatment.py
src/workflow/functions/intracellular/run_physiboss_step.py
src/workflow/functions/intercellular/apply_physiboss_phenotype.py
src/workflow/functions/intercellular/physiboss_cell_division.py
src/workflow/functions/intercellular/update_mechanics_physicell.py
```

**Tests, scripts, orphan workflows** that drove the dead code:

```
tests/test_physiboss_adapter.py
scripts/compare_native_physiboss.py
scripts/physiboss_poc.py
scripts/benchmark_mechanics.py
scripts/compare_mechanics_native.py
scripts/_debug_cell65.py
scripts/_debug_mechanics.py
opencellcomms_adapters/prostate/workflows/prostate_LNCaP.json
opencellcomms_gui/server/workflows/physiboss_tnf_tutorial.json
```

### What was patched

- `src/workflow/registry.py` (lines ~137–140): removed the dead imports.
- `src/workflow/functions/{initialization,intracellular,intercellular}/__init__.py`:
  pruned the now-orphan re-exports.
- `scripts/compare_prostate_native.py`: **kept** as the Phase 5 spec but
  tombstoned — running it as a script prints a Phase 5 notice and exits 2.
  The imports that targeted the deleted modules are commented out with a
  pointer to where Phase 5 will rewrite the script.

### What was kept (intentionally)

- `opencellcomms_adapters/prostate/` — the prostate experiment scaffold.
  Its `functions/intracellular/run_prostate_physiboss_step.py` has its
  own implementation and does *not* depend on the deleted engine modules.
- `scripts/compare_prostate_native.py` — Phase 5 regression target spec.

### How to verify Phase 0

The hard requirement is that the engine still imports cleanly:

```bash
cd opencellcomms_engine/
python -c "
import src.workflow.registry as r
reg = r.get_default_registry()
print(f'registry: {len(reg.functions)} functions')
"
```

Expected: `[KERNEL REGISTRY] Registered kernel: biophysics` then
`registry: 77 functions`. No `ImportError`.

A grep for residual references should return empty (modulo the
intentionally-commented imports in `compare_prostate_native.py`):

```bash
grep -rn 'src\.adapters\.physiboss\|src\.adapters\.physicell_mechanics' \
  opencellcomms_engine/src/
```

---

## Phase 1 — Observability runtime

The single piece of C++ that OpenCellComms owns permanently. Templates
copied verbatim into every generated PhysiCell project (Phase 2 wires
them in). Emits a JSON-Lines event stream so the GUI can render
per-rule / per-cell timelines without ever editing `PhysiBoSS-master/`.

### File layout

```
opencellcomms_engine/src/codegen/
├── __init__.py                                # codegen package marker
└── physicell/
    ├── __init__.py
    └── runtime/
        ├── __init__.py                        # exposes RUNTIME_DIR + paths
        ├── occ_observability.h
        └── occ_observability.cpp

opencellcomms_engine/tests/codegen/
├── __init__.py
└── test_observability_stub.py                 # validation harness
```

Phase 2's scaffold step finds the runtime sources via
`src.codegen.physicell.runtime.OBSERVABILITY_HEADER` /
`OBSERVABILITY_SOURCE`.

### Public C++ API

Declared in `occ_observability.h`:

```cpp
namespace occ {

// Truncates <output_dir>/occ_events.jsonl and sets the snapshot cadence.
// Call once at simulation startup (Phase 2 will inject this into custom.cpp).
void init(const std::string& output_dir, double save_interval_minutes);

// Append one event to the calling thread's buffer. Lock-free; safe inside
// OpenMP parallel regions. Field values must be numeric (the GUI parses
// them as floats); event/field names must be NUL-terminated C strings.
void emit(const char* event,
          int cell_id,
          double t,
          std::initializer_list<std::pair<const char*, double>> fields);

// True at most once per save_interval_minutes of PhysiCell simulated time.
// In standalone (non-PhysiCell) builds always returns false — the test
// harness flushes manually instead.
bool should_snapshot();

// Drain every thread's buffer to disk. Single-writer; call outside any
// parallel region.
void flush();

#ifdef OCC_HAS_PHYSICELL
void rules_observe_begin(PhysiCell::Cell* pCell);  // snapshot rates
void rules_observe_end  (PhysiCell::Cell* pCell);  // diff → emit changes
void emit_cell_snapshot (PhysiCell::Cell* pCell);  // periodic full state
#endif

}
```

The `Cell*`-taking functions are behind `OCC_HAS_PHYSICELL` so the
runtime is unit-testable in isolation. Phase 2's generated Makefile
defines `-DOCC_HAS_PHYSICELL` so the full surface is wired in.

### JSON-Lines event schema

Each `emit()` produces one line. Example:

```json
{"event":"test_event","cell_id":42,"t":1.5,"thread":2,"seq":7}
```

- `event` (string): event name, e.g. `rule_engine_changed`, `cell_snapshot`.
- `cell_id` (int): PhysiCell cell ID.
- `t` (number): simulation time in minutes.
- Remaining keys come straight from the `fields` initializer list (all
  numeric).

Special values: `NaN` and `±Inf` are encoded as JSON `null` so each line
remains parseable by strict JSON readers.

Events Phase 1 already knows how to emit (when built with `-DOCC_HAS_PHYSICELL`):

| Event | Fields | When |
|---|---|---|
| `rule_engine_changed` | `rate`, `from`, `to` | A rate changed between `rules_observe_begin` and `rules_observe_end`. The `rate` field is a small int tag: `0`=apoptosis, `1`=necrosis, `2`=migration_speed. Phase 3 widens this enum. |
| `cell_snapshot` | `x`, `y`, `z`, `volume` | `emit_cell_snapshot` called (typically at `should_snapshot()` boundaries). |

User-defined events emitted by Phase 5 fragments will appear here too.

### Threading & lifetime model

The non-obvious part of the implementation:

- Each thread, on its first `emit()`, **heap-allocates** a `std::string`
  buffer and registers the pointer in a global mutex-guarded vector
  (`all_buffers()`).
- The buffer is `new`'d on the heap and **outlives the thread** on
  purpose. `flush()` is typically called after worker threads have
  joined; if buffers were `thread_local`, their storage would already be
  gone. The vector is leaked at process exit — acceptable because
  `flush()` runs once on shutdown.
- `flush()` takes the global mutex, opens `occ_events.jsonl` in append
  mode, drains every buffer in order. No interleaving across threads.

This is the bug that was caught by the validation harness on the first
run (0 events written instead of 100) — the initial `thread_local
std::string` implementation lost its contents the moment a worker
exited. The fix is at `occ_observability.cpp` `tl_buffer_ptr()` /
`ensure_registered()`.

### Design choices worth knowing

- **Zero external deps.** Hand-written JSON writer (no nlohmann,
  RapidJSON, etc.). Means the runtime builds against the upstream
  Makefile's existing CFLAGS unchanged — important for Phase 2.
- **`init()` was added to the plan's API.** The original plan listed
  five entry points; we added `init()` so the output path and snapshot
  cadence are configurable (essential for the test harness; also useful
  per-experiment).
- **C++17, OpenMP-independent.** The harness uses `std::thread` rather
  than `#pragma omp parallel` so the test works on stock Apple clang
  (which doesn't ship libomp). The threading model being validated is
  the same one OpenMP uses.

---

## Testing

### Automated harness

```bash
cd opencellcomms_engine/
python -m pytest tests/codegen/test_observability_stub.py -v
```

What this exercises:

1. `test_observability_emits_well_formed_jsonl` — 4 threads × 25 emits
   each → 100 events. Asserts every line parses as JSON, every thread
   id 0..3 appears, every event has the expected shape.
2. `test_init_truncates_existing_file` — runs the driver twice in the
   same output dir. Asserts the second run starts from scratch (i.e.
   `init()` truncates the file).

Both should pass in ~15 seconds (most of the time is two C++ compiles).
Requires `c++` (or `g++` / `clang++`) on PATH; skips otherwise.

### Manual / interactive build

To poke at the runtime by hand without pytest:

```bash
cd /tmp && rm -rf occ_play && mkdir occ_play && cd occ_play
cp <repo>/opencellcomms_engine/src/codegen/physicell/runtime/occ_observability.{h,cpp} .

cat > driver.cpp <<'EOF'
#include "occ_observability.h"
#include <thread>
#include <vector>
int main() {
    occ::init("./out", /*save_interval_min=*/30.0);
    std::vector<std::thread> ws;
    for (int t = 0; t < 4; ++t) ws.emplace_back([t]{
        for (int i = 0; i < 25; ++i)
            occ::emit("hello", t*100+i, i*0.5,
                      {{"thread", (double)t}, {"seq", (double)i}});
    });
    for (auto& w : ws) w.join();
    occ::flush();
}
EOF

mkdir -p out
c++ -std=c++17 -O0 -pthread driver.cpp occ_observability.cpp -o driver
./driver
cat out/occ_events.jsonl | head
wc -l out/occ_events.jsonl
```

Expected: 100 lines, each a one-line JSON object.

You can pipe through `jq` for nicer inspection:

```bash
jq -c 'select(.thread == 2)' out/occ_events.jsonl   # one thread's events
jq -s 'group_by(.thread) | map(length)' out/occ_events.jsonl  # 25 per thread
```

### Edge cases worth probing

- **Re-running the binary** should produce exactly 100 events (the test
  covers this; `init()` truncates).
- **Removing the `occ::flush()` call** from `driver.cpp` should result
  in an empty file — events stay buffered without an explicit drain.
  This validates that nothing else is sneaking in writes.
- **NaN handling**: `occ::emit("bad", 0, 0.0, {{"v", std::nan("")}})`
  produces `…,"v":null` rather than an unparseable line.

---

## What Phase 1 deliberately does NOT include

Sticky points to remember when reviewing the C++ before Phase 2 ships:

- **No real PhysiCell integration yet.** `rules_observe_begin/end` only
  snapshots three phenotype fields (apoptosis rate, necrosis rate,
  migration speed) — picked because they exist in all upstream versions.
  Phase 3 widens the snapshot to every behavior the Hill-rules grammar
  can write to.
- **No `setup_microenvironment` shim.** Phase 2 generates the
  `custom.cpp` that calls `occ::init` at startup and `occ::flush` at
  shutdown.
- **No Makefile.** Phase 2 generates one from the upstream
  `rules_sample/Makefile` template with `-DOCC_HAS_PHYSICELL` added.
- **No GUI consumer.** Phase 4 adds the event tail in the Flask /
  React layer.

---

## File index (quick navigation)

| File | Purpose |
|---|---|
| `opencellcomms_engine/src/codegen/__init__.py` | Codegen package marker |
| `opencellcomms_engine/src/codegen/physicell/__init__.py` | PhysiCell-codegen package marker |
| `opencellcomms_engine/src/codegen/physicell/runtime/__init__.py` | Exposes `OBSERVABILITY_HEADER`, `OBSERVABILITY_SOURCE` paths for Phase 2 |
| `opencellcomms_engine/src/codegen/physicell/runtime/occ_observability.h` | Public C++ API |
| `opencellcomms_engine/src/codegen/physicell/runtime/occ_observability.cpp` | Implementation |
| `opencellcomms_engine/tests/codegen/test_observability_stub.py` | Validation harness (2 tests) |
| `opencellcomms_engine/scripts/compare_prostate_native.py` | Tombstoned; Phase 5 spec |

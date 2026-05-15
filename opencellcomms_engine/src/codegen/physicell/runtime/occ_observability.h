// occ_observability.h — OpenCellComms observability runtime.
//
// The single piece of C++ owned by OpenCellComms; copied verbatim into
// every generated PhysiCell project (see docs/Physicell_Facade_plan.md).
//
// Emits a JSON-Lines event stream at <output_dir>/occ_events.jsonl so the
// GUI can render per-cell / per-rule timelines without ever editing the
// upstream PhysiBoSS-master tree.
//
// Threading: per-thread buffer, single-writer flush. Safe to call emit()
// from inside OpenMP parallel regions.
//
// Build modes:
//   - Default: header-only-clean; emit/flush/init/should_snapshot work
//     without any PhysiCell headers — used by the Phase 1 standalone test.
//   - -DOCC_HAS_PHYSICELL: enables rules_observe_begin / rules_observe_end /
//     emit_cell_snapshot, which take PhysiCell::Cell*.

#ifndef OCC_OBSERVABILITY_H
#define OCC_OBSERVABILITY_H

#include <initializer_list>
#include <string>
#include <utility>

#ifdef OCC_HAS_PHYSICELL
namespace PhysiCell { class Cell; }
#endif

namespace occ {

// Configure output path and snapshot cadence. Truncates any existing
// occ_events.jsonl in <output_dir>. Call once at simulation startup
// (e.g. from setup_microenvironment in the generated custom.cpp).
void init(const std::string& output_dir, double save_interval_minutes);

// Append one event to the calling thread's buffer. Lock-free.
void emit(const char* event,
          int cell_id,
          double t,
          std::initializer_list<std::pair<const char*, double>> fields);

// True at most once per save_interval_minutes of PhysiCell simulated time.
// Always returns false in standalone (non-PhysiCell) builds; the test
// harness drives flushing manually instead.
bool should_snapshot();

// Drain every registered thread buffer into the JSONL file. Single writer;
// safe to call from outside OpenMP parallel regions.
void flush();

#ifdef OCC_HAS_PHYSICELL
// Snapshot the phenotype rates that the upstream rules engine can touch.
void rules_observe_begin(PhysiCell::Cell* pCell);
// Diff vs. the snapshot taken at begin; emit one rule_engine_changed
// event per rate that moved.
void rules_observe_end(PhysiCell::Cell* pCell);
// Periodic full-state dump for the GUI's per-cell timeline view.
void emit_cell_snapshot(PhysiCell::Cell* pCell);
#endif

} // namespace occ

#endif // OCC_OBSERVABILITY_H

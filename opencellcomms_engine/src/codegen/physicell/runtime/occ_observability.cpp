// occ_observability.cpp — see occ_observability.h for the contract.
//
// Implementation notes:
//   - Each thread, on its first emit(), heap-allocates a std::string and
//     registers the pointer in a process-global, mutex-guarded vector.
//     The buffer outlives the thread on purpose: flush() can be called
//     after worker threads have already joined. The vector is leaked at
//     process exit (acceptable — flush() runs once on shutdown).
//   - We hand-write JSON (not nlohmann::json or similar) so the runtime has
//     zero external dependencies and builds against the upstream Makefile's
//     existing CFLAGS unchanged.

#include "occ_observability.h"

#include <cmath>
#include <cstdio>
#include <fstream>
#include <map>
#include <mutex>
#include <string>
#include <vector>

#ifdef OCC_HAS_PHYSICELL
#include "../core/PhysiCell.h"
#endif

namespace occ {

namespace {

struct Config {
    std::string output_path = "output/occ_events.jsonl";
    double save_interval_min = 30.0;
    double last_snapshot_time = -1.0;
    bool initialized = false;
};

Config& cfg() {
    static Config c;
    return c;
}

std::mutex& buffers_mutex() {
    static std::mutex m;
    return m;
}

std::vector<std::string*>& all_buffers() {
    static std::vector<std::string*> v;
    return v;
}

std::string*& tl_buffer_ptr() {
    static thread_local std::string* p = nullptr;
    return p;
}

std::string& ensure_registered() {
    std::string*& p = tl_buffer_ptr();
    if (p) return *p;
    auto* s = new std::string();
    s->reserve(4096);
    {
        std::lock_guard<std::mutex> lk(buffers_mutex());
        all_buffers().push_back(s);
    }
    p = s;
    return *s;
}

void write_json_string(std::string& out, const char* s) {
    out += '"';
    for (const char* p = s; *p; ++p) {
        char c = *p;
        if (c == '"' || c == '\\') { out += '\\'; out += c; }
        else if (c == '\n') out += "\\n";
        else if (c == '\r') out += "\\r";
        else if (c == '\t') out += "\\t";
        else out += c;
    }
    out += '"';
}

void write_json_number(std::string& out, double v) {
    if (std::isnan(v) || std::isinf(v)) {
        // JSON has no NaN/Inf token; encode as null so the line stays valid.
        out += "null";
        return;
    }
    char buf[32];
    int n = std::snprintf(buf, sizeof(buf), "%.17g", v);
    if (n > 0) out.append(buf, static_cast<size_t>(n));
}

} // namespace

void init(const std::string& output_dir, double save_interval_minutes) {
    Config& c = cfg();
    c.output_path = output_dir + "/occ_events.jsonl";
    c.save_interval_min = save_interval_minutes;
    c.last_snapshot_time = -1.0;
    c.initialized = true;
    // Truncate so re-runs do not append to stale data.
    std::ofstream f(c.output_path, std::ios::trunc);
}

void emit(const char* event,
          int cell_id,
          double t,
          std::initializer_list<std::pair<const char*, double>> fields)
{
    std::string& buf = ensure_registered();
    buf += "{\"event\":";
    write_json_string(buf, event);
    buf += ",\"cell_id\":";
    char idbuf[16];
    std::snprintf(idbuf, sizeof(idbuf), "%d", cell_id);
    buf += idbuf;
    buf += ",\"t\":";
    write_json_number(buf, t);
    for (const auto& kv : fields) {
        buf += ',';
        write_json_string(buf, kv.first);
        buf += ':';
        write_json_number(buf, kv.second);
    }
    buf += "}\n";
}

void flush() {
    Config& c = cfg();
    if (!c.initialized) return;
    std::lock_guard<std::mutex> lk(buffers_mutex());
    std::ofstream f(c.output_path, std::ios::app);
    if (!f) return;
    for (std::string* buf : all_buffers()) {
        if (buf && !buf->empty()) {
            f.write(buf->data(), static_cast<std::streamsize>(buf->size()));
            buf->clear();
        }
    }
}

#ifdef OCC_HAS_PHYSICELL

bool should_snapshot() {
    double now = PhysiCell::PhysiCell_globals.current_time;
    Config& c = cfg();
    if (c.last_snapshot_time < 0.0) {
        c.last_snapshot_time = now;
        return false;
    }
    if (now - c.last_snapshot_time >= c.save_interval_min) {
        c.last_snapshot_time = now;
        return true;
    }
    return false;
}

namespace {

// Phase 1 captures three well-known phenotype fields. Phase 3 extends the
// snapshot to cover every behavior the Hill-rules grammar can write to.
struct RateSnapshot {
    double apoptosis_rate = 0.0;
    double necrosis_rate = 0.0;
    double migration_speed = 0.0;
};

std::map<int, RateSnapshot>& observe_table() {
    static thread_local std::map<int, RateSnapshot> t;
    return t;
}

RateSnapshot snapshot(PhysiCell::Cell* pCell) {
    RateSnapshot s;
    if (pCell->phenotype.death.rates.size() > 0)
        s.apoptosis_rate = pCell->phenotype.death.rates[0];
    if (pCell->phenotype.death.rates.size() > 1)
        s.necrosis_rate  = pCell->phenotype.death.rates[1];
    s.migration_speed = pCell->phenotype.motility.migration_speed;
    return s;
}

// 'rate' field on rule_engine_changed events is a small integer tag so the
// GUI can group by rate without parsing names. Phase 3 widens this enum.
constexpr double kRateApoptosis      = 0.0;
constexpr double kRateNecrosis       = 1.0;
constexpr double kRateMigrationSpeed = 2.0;

} // namespace

void rules_observe_begin(PhysiCell::Cell* pCell) {
    observe_table()[pCell->ID] = snapshot(pCell);
}

void rules_observe_end(PhysiCell::Cell* pCell) {
    auto it = observe_table().find(pCell->ID);
    if (it == observe_table().end()) return;
    RateSnapshot before = it->second;
    RateSnapshot after = snapshot(pCell);
    observe_table().erase(it);

    double t = PhysiCell::PhysiCell_globals.current_time;
    if (before.apoptosis_rate != after.apoptosis_rate) {
        emit("rule_engine_changed", pCell->ID, t,
             {{"rate", kRateApoptosis},
              {"from", before.apoptosis_rate},
              {"to",   after.apoptosis_rate}});
    }
    if (before.necrosis_rate != after.necrosis_rate) {
        emit("rule_engine_changed", pCell->ID, t,
             {{"rate", kRateNecrosis},
              {"from", before.necrosis_rate},
              {"to",   after.necrosis_rate}});
    }
    if (before.migration_speed != after.migration_speed) {
        emit("rule_engine_changed", pCell->ID, t,
             {{"rate", kRateMigrationSpeed},
              {"from", before.migration_speed},
              {"to",   after.migration_speed}});
    }
}

void emit_cell_snapshot(PhysiCell::Cell* pCell) {
    double t = PhysiCell::PhysiCell_globals.current_time;
    emit("cell_snapshot", pCell->ID, t,
         {{"x", pCell->position[0]},
          {"y", pCell->position[1]},
          {"z", pCell->position[2]},
          {"volume", pCell->phenotype.volume.total}});
}

#else  // !OCC_HAS_PHYSICELL — standalone build used by the Phase 1 test

bool should_snapshot() {
    // Standalone callers drive flushing manually.
    return false;
}

#endif // OCC_HAS_PHYSICELL

} // namespace occ

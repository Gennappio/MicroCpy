"""Phase 1 validation harness for the PhysiCell black-box facade.

Compiles ``occ_observability.{h,cpp}`` in standalone mode (no PhysiCell
headers needed), runs a small multi-threaded driver that emits exactly
100 events, and asserts the JSONL stream is well-formed.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from opencellcomms_adapters.PhysiBoSS.codegen.runtime import (
    OBSERVABILITY_HEADER,
    OBSERVABILITY_SOURCE,
)

NUM_THREADS = 4
EMITS_PER_THREAD = 25
TOTAL_EMITS = NUM_THREADS * EMITS_PER_THREAD


def _find_compiler() -> str | None:
    for candidate in ("c++", "g++", "clang++"):
        if shutil.which(candidate):
            return candidate
    return None


DRIVER_CPP = r"""
#include "occ_observability.h"

#include <thread>
#include <vector>

int main(int argc, char** argv) {
    if (argc < 2) return 2;
    occ::init(argv[1], /*save_interval_min=*/30.0);

    const int kThreads = NUM_THREADS;
    const int kPerThread = EMITS_PER_THREAD;

    std::vector<std::thread> workers;
    workers.reserve(kThreads);
    for (int tid = 0; tid < kThreads; ++tid) {
        workers.emplace_back([tid] {
            for (int i = 0; i < kPerThread; ++i) {
                occ::emit("test_event",
                          /*cell_id=*/tid * 1000 + i,
                          /*t=*/static_cast<double>(i) * 0.5,
                          {{"thread", static_cast<double>(tid)},
                           {"seq", static_cast<double>(i)}});
            }
        });
    }
    for (auto& w : workers) w.join();

    occ::flush();
    return 0;
}
"""


@pytest.fixture
def stub_workspace(tmp_path: Path) -> Path:
    """Materialize sources + driver + output dir in a clean temp tree."""
    workspace = tmp_path / "stub"
    workspace.mkdir()
    (workspace / "output").mkdir()

    shutil.copy(OBSERVABILITY_HEADER, workspace / "occ_observability.h")
    shutil.copy(OBSERVABILITY_SOURCE, workspace / "occ_observability.cpp")

    driver = (
        DRIVER_CPP
        .replace("NUM_THREADS", str(NUM_THREADS))
        .replace("EMITS_PER_THREAD", str(EMITS_PER_THREAD))
    )
    (workspace / "driver.cpp").write_text(driver)
    return workspace


def test_observability_emits_well_formed_jsonl(stub_workspace: Path) -> None:
    compiler = _find_compiler()
    if compiler is None:
        pytest.skip("no C++ compiler in PATH (need c++/g++/clang++)")

    binary = stub_workspace / "driver"
    compile_cmd = [
        compiler,
        "-std=c++17",
        "-O0",
        "-pthread",
        "driver.cpp",
        "occ_observability.cpp",
        "-o",
        str(binary),
    ]
    result = subprocess.run(
        compile_cmd, cwd=stub_workspace, capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.fail(
            f"compilation failed:\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    run = subprocess.run(
        [str(binary), "output"],
        cwd=stub_workspace,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert run.returncode == 0, (
        f"driver exited {run.returncode}\nstdout: {run.stdout}\n"
        f"stderr: {run.stderr}"
    )

    jsonl_path = stub_workspace / "output" / "occ_events.jsonl"
    assert jsonl_path.exists(), "occ_events.jsonl was not written"

    lines = [ln for ln in jsonl_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == TOTAL_EMITS, (
        f"expected {TOTAL_EMITS} events, got {len(lines)}"
    )

    seen_threads: set[int] = set()
    for ln in lines:
        evt = json.loads(ln)
        assert evt["event"] == "test_event"
        assert isinstance(evt["cell_id"], int)
        assert isinstance(evt["t"], (int, float))
        assert "thread" in evt and "seq" in evt
        seen_threads.add(int(evt["thread"]))

    assert seen_threads == set(range(NUM_THREADS)), (
        f"expected events from threads {set(range(NUM_THREADS))}, "
        f"got {seen_threads}"
    )


def test_init_truncates_existing_file(stub_workspace: Path) -> None:
    """A second run on the same output_dir must not append to the prior run."""
    compiler = _find_compiler()
    if compiler is None:
        pytest.skip("no C++ compiler in PATH")

    binary = stub_workspace / "driver"
    subprocess.run(
        [
            compiler,
            "-std=c++17",
            "-O0",
            "-pthread",
            "driver.cpp",
            "occ_observability.cpp",
            "-o",
            str(binary),
        ],
        cwd=stub_workspace,
        check=True,
        capture_output=True,
    )

    for _ in range(2):
        subprocess.run(
            [str(binary), "output"], cwd=stub_workspace, check=True, timeout=30
        )

    jsonl_path = stub_workspace / "output" / "occ_events.jsonl"
    lines = [ln for ln in jsonl_path.read_text().splitlines() if ln.strip()]
    assert len(lines) == TOTAL_EMITS, (
        "init() did not truncate prior run's events; "
        f"got {len(lines)} lines, expected {TOTAL_EMITS}"
    )

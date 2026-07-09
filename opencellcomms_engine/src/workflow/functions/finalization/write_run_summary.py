"""
Write a machine-readable run_summary.json for automated review.

Where the other finalization functions produce human-facing artifacts (plots,
per-step CSVs), this one distills a run into a single small JSON that an agent or
a CI step can parse to judge whether the simulation behaved: final cell/substance
statistics, per-substance trajectories (when the workflow recorded them), health
flags (non-finite fields, blow-ups), and the paths of the plots produced. It is
consumed by the /occ_review-run skill.
"""

from typing import Dict, Any
from pathlib import Path
import json

from src.workflow.decorators import register_function


def _as_list(v):
    """Best-effort convert a scalar / numpy array / iterable to a JSON list."""
    if v is None:
        return None
    if hasattr(v, "tolist"):
        return v.tolist()
    if hasattr(v, "__iter__"):
        return list(v)
    return [v]


@register_function(
    display_name="Write Run Summary",
    description="Write run_summary.json (final stats, substance trajectories, health flags, plot paths) for automated review",
    category="FINALIZATION",
    compatible_kernels=["*"],
    requires=[],
    parameters=[
        {
            "name": "blowup_threshold",
            "type": "FLOAT",
            "description": "Flag a substance as a possible blow-up if any |concentration| exceeds this",
            "default": 1e12,
        }
    ],
    outputs=["run_summary"],
    cloneable=False,
)
def write_run_summary(
    context: Dict[str, Any],
    blowup_threshold: float = 1e12,
    **kwargs,
) -> bool:
    """Assemble and write results/run_summary.json. Reads whatever is available;
    a missing population or simulator degrades the summary rather than failing."""
    print("[WORKFLOW] Writing run summary...")

    try:
        import numpy as np

        config = context.get("config")
        if "output_dir" in context:
            output_dir = Path(context["output_dir"])
        elif hasattr(config, "output_dir"):
            output_dir = Path(config.output_dir)
        else:
            output_dir = Path("results")
        output_dir.mkdir(parents=True, exist_ok=True)

        summary: Dict[str, Any] = {
            "steps": context.get("current_step", getattr(config, "total_steps", None)),
            "dt": getattr(config, "dt", None),
            "cells": {},
            "substances": {},
            "health": {"ok": True, "flags": []},
            "plots": [],
        }

        # --- Cells: reuse collect_statistics output if present, else compute. ---
        final_stats = context.get("final_statistics") or {}
        population = context.get("population")
        if final_stats.get("cell_statistics"):
            summary["cells"] = final_stats["cell_statistics"]
        elif population is not None:
            cells = population.state.cells
            counts: Dict[str, int] = {}
            for cell in cells.values():
                ph = cell.state.phenotype
                counts[ph] = counts.get(ph, 0) + 1
            summary["cells"] = {
                "total_cells": len(cells),
                "phenotype_distribution": counts,
            }

        # --- Substances: final snapshot + trajectory (if recorded) + health. ---
        results = context.get("results", {}) or {}
        trajectories = results.get("substance_stats", {}) or {}
        simulator = context.get("simulator")
        if simulator is not None and hasattr(simulator, "get_substance_concentrations"):
            for name, grid in simulator.get_substance_concentrations().items():
                if hasattr(grid, "value"):
                    vals = np.asarray(grid.value, dtype=float).flatten()
                elif isinstance(grid, dict):
                    vals = np.asarray(list(grid.values()), dtype=float)
                else:
                    vals = np.asarray([grid], dtype=float)

                finite = np.isfinite(vals)
                entry: Dict[str, Any] = {}
                if finite.any():
                    fv = vals[finite]
                    entry["final"] = {
                        "min": float(np.min(fv)),
                        "mean": float(np.mean(fv)),
                        "max": float(np.max(fv)),
                    }
                if not finite.all():
                    summary["health"]["ok"] = False
                    summary["health"]["flags"].append(f"{name}: non-finite values (NaN/Inf)")
                elif float(np.max(np.abs(vals))) > blowup_threshold:
                    summary["health"]["ok"] = False
                    summary["health"]["flags"].append(
                        f"{name}: possible blow-up (|concentration| > {blowup_threshold:g})"
                    )

                traj = trajectories.get(name)
                if isinstance(traj, dict):
                    entry["trajectory"] = {
                        k: _as_list(traj.get(k)) for k in ("mean", "min", "max") if k in traj
                    }
                summary["substances"][name] = entry

        if "time" in results:
            try:
                summary["time_points"] = int(len(results["time"]))
            except TypeError:
                pass

        # --- Plots produced this run. ---
        plots_dir = Path(context.get("plots_dir") or (output_dir / "plots"))
        if plots_dir.exists():
            summary["plots"] = sorted(str(p) for p in plots_dir.rglob("*.png"))

        with open(output_dir / "run_summary.json", "w") as f:
            json.dump(summary, f, indent=2)
        context["run_summary"] = summary

        health = "ok" if summary["health"]["ok"] else "FLAGGED: " + "; ".join(summary["health"]["flags"])
        print(f"   [OK] run_summary.json written to {output_dir} (health: {health})")
        return True

    except Exception as e:
        print(f"[WORKFLOW] Error writing run summary: {e}")
        import traceback

        traceback.print_exc()
        return False

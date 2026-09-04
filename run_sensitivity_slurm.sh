#!/bin/bash
#SBATCH --job-name="microc_p53_sa"
#SBATCH --array=0-11
#SBATCH --mem=80000
#SBATCH --account=abbruzzese
#SBATCH --partition=medium_gpunew
#SBATCH --output=slurm_logs/%x_%A_%a.out
#SBATCH --error=slurm_logs/%x_%A_%a.err
#SBATCH --mail-type=END
#SBATCH --mail-user=gennaro.abbruzzese@unibocconi.it
#SBATCH --cpus-per-task=8

#
# Run the p53 sensitivity suite as a SLURM job array: one task per Planner arm
# of the workflows in opencellcomms_adapters/MicroC/workflows/sensitivity_analysis/
# (four files x three levels = 12 arms, array indices 0-11).
#
#   mkdir -p slurm_logs                        # SLURM will not create the log dir
#   bash run_microc_slurm.sh --install-only    # build .venv-hpc ONCE, before the array
#   bash run_sensitivity_slurm.sh --list       # index -> workflow, tab (no SLURM needed)
#   sbatch run_sensitivity_slurm.sh            # all arms, in parallel
#   sbatch --array=0-11%4 run_sensitivity_slurm.sh   # at most four at a time
#   sbatch --array=2,7 run_sensitivity_slurm.sh      # a subset, by index from --list
#
# Each task delegates to run_microc_slurm.sh with the arm's workflow and tab,
# so venv activation, the headless settings and the run itself are shared with
# the single-workflow launcher; --no-observability is passed because twelve
# concurrent runs must not write the rolling debugger snapshots into the same
# engine-local folder. Results land in runs/<workflow stem>_<tab>/ with the
# executed workflow copied at the run root. Collect them afterwards with:
#   python opencellcomms_adapters/MicroC/workflows/sensitivity_analysis/collect_sensitivity_results.py
#
# The arm table is read from the workflow files at run time (enabled tabs, files
# in name order), so it follows the suite; if the number of arms changes, pass
# the matching --array range on the sbatch command line.

set -euo pipefail

REPO_ROOT="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
SUITE_DIR="${MICROC_SA_DIR:-$REPO_ROOT/opencellcomms_adapters/MicroC/workflows/sensitivity_analysis}"
VENV="${MICROC_VENV:-$REPO_ROOT/.venv-hpc}"
PYTHON="${MICROC_PYTHON:-python3}"
LAUNCHER="$REPO_ROOT/run_microc_slurm.sh"

[ -d "$SUITE_DIR" ] || { echo "ERROR: suite folder not found: $SUITE_DIR" >&2; exit 1; }
[ -f "$LAUNCHER" ] || { echo "ERROR: launcher not found: $LAUNCHER" >&2; exit 1; }

# One line per arm: "<workflow path><TAB><tab name>", every enabled Planner tab
# of every p53_sa_*.json, files in name order. Standard library only.
arm_table() {
    "$PYTHON" - "$SUITE_DIR" <<'PY'
import json, sys
from pathlib import Path
suite = Path(sys.argv[1])
for wf in sorted(suite.glob("p53_sa_*.json")):
    doc = json.loads(wf.read_text(encoding="utf-8"))
    tabs = doc.get("metadata", {}).get("gui", {}).get("planner", {}).get("tabs", [])
    for tab in tabs:
        if tab.get("enabled"):
            print(f"{wf}\t{tab['name']}")
PY
}

ARMS=()
while IFS= read -r line; do
    ARMS+=("$line")
done < <(arm_table)
N=${#ARMS[@]}
[ "$N" -gt 0 ] || { echo "ERROR: no enabled Planner tabs found under $SUITE_DIR" >&2; exit 1; }

if [ "${1:-}" = "--list" ]; then
    echo "$N arm(s); submit with: sbatch --array=0-$((N - 1)) run_sensitivity_slurm.sh"
    printf '%-6s %-40s %s\n' "index" "tab" "workflow"
    for i in $(seq 0 $((N - 1))); do
        IFS=$'\t' read -r wf tab <<< "${ARMS[$i]}"
        printf '%-6s %-40s %s\n' "$i" "$tab" "${wf#$REPO_ROOT/}"
    done
    exit 0
fi

INDEX="${SLURM_ARRAY_TASK_ID:-}"
[ -n "$INDEX" ] || { echo "ERROR: submit this script as a job array (sbatch run_sensitivity_slurm.sh) or run it with --list" >&2; exit 1; }
[ "$INDEX" -lt "$N" ] || { echo "ERROR: array index $INDEX but only $N arm(s) (0-$((N - 1))); see --list" >&2; exit 1; }

# The venv is built by run_microc_slurm.sh on its first run. Twelve tasks
# starting at once would race to create it, so an array task refuses to be the
# one that installs: prebuild with `bash run_microc_slurm.sh --install-only`.
[ -d "$VENV" ] || { echo "ERROR: venv not found at $VENV -- run 'bash run_microc_slurm.sh --install-only' before submitting the array" >&2; exit 1; }

IFS=$'\t' read -r WORKFLOW TAB <<< "${ARMS[$INDEX]}"
echo "sensitivity arm $INDEX/$((N - 1)): ${WORKFLOW#$REPO_ROOT/} :: $TAB"

cd "$REPO_ROOT"
MICROC_WORKFLOW="$WORKFLOW" MICROC_EXTRA_ARGS="--no-observability" \
    exec bash "$LAUNCHER" "$TAB"

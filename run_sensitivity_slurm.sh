#!/bin/bash
#SBATCH --job-name="microc_p53_sa"
#SBATCH --mem=80000
#SBATCH --account=abbruzzese
#SBATCH --partition=long_gpunew
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err
#SBATCH --mail-type=END
#SBATCH --mail-user=gennaro.abbruzzese@unibocconi.it
#SBATCH --cpus-per-task=8

# From the repository root, run one suite workflow per SLURM job (the jobs run
# concurrently; each gets its own runs/<name>_<timestamp> folder):
#   for f in opencellcomms_adapters/MicroC/workflows/sensitivity_analysis/p53_sa_*.json; do
#       sbatch run_sensitivity_slurm.sh "$f"
#   done
# or the full suite in one sequential job:
#   sbatch run_sensitivity_slurm.sh
# Planner tabs, replicate counts and seed settings all come from the five
# workflow JSON files. Edit/export those workflows to change the plan. Within a
# job, runs execute sequentially, with separate configuration/replicate/attempt
# folders.
# One-time environment setup: bash run_microc_slurm.sh --install-only
# The result folder records execution provenance automatically; users never
# prepare or edit a second plan file.

set -euo pipefail
REPO_ROOT="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
VENV="${MICROC_VENV:-$REPO_ROOT/.venv-hpc}"
PYTHON="${MICROC_PYTHON:-$VENV/bin/python}"
SUITE_DIR="${MICROC_SA_DIR:-$REPO_ROOT/opencellcomms_adapters/MicroC/workflows/sensitivity_analysis}"
RUNS_DIR="${MICROC_RUNS_DIR:-$REPO_ROOT/runs}"
RUNNER="$REPO_ROOT/opencellcomms_engine/tools/run_planner_batch.py"
cd "$REPO_ROOT"
export MPLBACKEND=Agg PYTHONUNBUFFERED=1 PYTHONHASHSEED=0
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-${MICROC_THREADS:-8}}"
export OPENBLAS_NUM_THREADS="$OMP_NUM_THREADS" MKL_NUM_THREADS="$OMP_NUM_THREADS"
command -v "$PYTHON" >/dev/null 2>&1 || {
    echo "Python environment not found: $PYTHON" >&2
    echo "Set it up once with: bash run_microc_slurm.sh --install-only" >&2
    exit 1
}
[ "$#" -le 1 ] || {
    echo "Pass one suite workflow JSON to run it alone, or nothing to run the whole suite; the plan itself comes from the workflow files." >&2
    exit 2
}
[ -z "${SLURM_ARRAY_TASK_ID:-}" ] || {
    echo "Submit this as one job, without --array. Replication is already in the workflow plan." >&2
    exit 2
}
if [ "$#" -eq 1 ]; then
    exec "$PYTHON" "$RUNNER" --workflow "$1" --runs-dir "$RUNS_DIR"
fi
exec "$PYTHON" "$RUNNER" --suite "$SUITE_DIR" --runs-dir "$RUNS_DIR"

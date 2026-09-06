#!/bin/bash
#SBATCH --job-name="microc_p53_sa"
#SBATCH --mem=80000
#SBATCH --account=abbruzzese
#SBATCH --partition=medium_gpunew
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err
#SBATCH --mail-type=END
#SBATCH --mail-user=gennaro.abbruzzese@unibocconi.it
#SBATCH --cpus-per-task=8

# From the repository root, run the full suite in one SLURM job:
#   sbatch run_sensitivity_slurm.sh
# Replicate counts/seeds come from the workflow files. To choose a new default:
#   sbatch run_sensitivity_slurm.sh --replicates N --master-seed SEED
# N and SEED are user-chosen positive integers. All runs execute sequentially,
# with one saved plan and separate configuration/replicate/attempt folders.
# One-time environment setup: bash run_microc_slurm.sh --install-only
#
# Optional parallel array mode: prepare a frozen manifest first:
#   bash run_sensitivity_slurm.sh --prepare --replicates 10 --master-seed 42
# Then use the printed manifest path and array range:
#   sbatch --array=0-119%4 run_sensitivity_slurm.sh runs/<batch>/manifest.json
# Re-submitting an index skips completed valid runs; failed attempts retain
# their seed and receive a new attempt folder. No live workflow expansion occurs
# on the compute nodes. Do not edit model code while a batch is in progress.

set -euo pipefail
REPO_ROOT="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
VENV="${MICROC_VENV:-$REPO_ROOT/.venv-hpc}"
PYTHON="${MICROC_PYTHON:-$VENV/bin/python}"
SUITE_DIR="${MICROC_SA_DIR:-$REPO_ROOT/opencellcomms_adapters/MicroC/workflows/sensitivity_analysis}"
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
if [ "${1:-}" = "--prepare" ]; then
    shift
    exec "$PYTHON" "$RUNNER" --suite "$SUITE_DIR" --prepare "$@"
fi
if [ "${1:-}" = "--list" ]; then
    shift
    exec "$PYTHON" "$RUNNER" --manifest "${1:?Provide the saved manifest path}" --status
fi
MANIFEST="${MICROC_SA_MANIFEST:-}"
if [ "$#" -gt 0 ] && [[ "$1" != -* ]]; then
    MANIFEST="$1"
    shift
fi
if [ -n "$MANIFEST" ]; then
    [ -f "$MANIFEST" ] || { echo "Saved manifest not found: $MANIFEST" >&2; exit 1; }
    RUN_ARGS=(--manifest "$MANIFEST")
    if [ -n "${SLURM_ARRAY_TASK_ID:-}" ]; then
        RUN_ARGS+=(--index "$SLURM_ARRAY_TASK_ID")
    fi
    exec "$PYTHON" "$RUNNER" "${RUN_ARGS[@]}" "$@"
fi
if [ -n "${SLURM_ARRAY_TASK_ID:-}" ]; then
    echo "Array jobs require a saved manifest. Use --prepare first, or submit without --array for the full suite in one job." >&2
    exit 1
fi
exec "$PYTHON" "$RUNNER" --suite "$SUITE_DIR" "$@"

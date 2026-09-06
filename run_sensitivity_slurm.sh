#!/bin/bash
#SBATCH --job-name="microc_p53_sa"
#SBATCH --mem=80000
#SBATCH --account=abbruzzese
#SBATCH --partition=medium_gpunew
#SBATCH --output=slurm_logs/%x_%A_%a.out
#SBATCH --error=slurm_logs/%x_%A_%a.err
#SBATCH --mail-type=END
#SBATCH --mail-user=gennaro.abbruzzese@unibocconi.it
#SBATCH --cpus-per-task=8

# Prepare a frozen manifest with the same environment used by the workers:
#   bash run_microc_slurm.sh --install-only
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
export OMP_NUM_THREADS="${MICROC_THREADS:-8}"
export OPENBLAS_NUM_THREADS="$OMP_NUM_THREADS" MKL_NUM_THREADS="$OMP_NUM_THREADS"
mkdir -p slurm_logs
if [ "${1:-}" = "--prepare" ]; then
    shift
    exec "$PYTHON" "$RUNNER" --suite "$SUITE_DIR" --prepare "$@"
fi
if [ "${1:-}" = "--list" ]; then
    shift
    exec "$PYTHON" "$RUNNER" --manifest "${1:?Provide the saved manifest path}" --status
fi
MANIFEST="${1:-${MICROC_SA_MANIFEST:-}}"
[ -f "$MANIFEST" ] || { echo "Provide a frozen manifest; create it first with --prepare." >&2; exit 1; }
INDEX="${SLURM_ARRAY_TASK_ID:?Submit with --array matching the saved manifest}"
exec "$PYTHON" "$RUNNER" --manifest "$MANIFEST" --index "$INDEX"

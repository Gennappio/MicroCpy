#!/bin/bash
#SBATCH --job-name="microc_p53_sa_new"
#SBATCH --mem=80000
#SBATCH --account=abbruzzese
#SBATCH --partition=long_gpunew
#SBATCH --output=%x_%j.out
#SBATCH --error=%x_%j.err
#SBATCH --mail-type=END
#SBATCH --mail-user=gennaro.abbruzzese@unibocconi.it
#SBATCH --cpus-per-task=8

# Run ONLY the arms added when three sweeps were mirrored to their stable side
# (o2_cons_13.2, glc_bnd_4.5 and domain_1800 were numerically unstable and were
# replaced by o2_cons_6.6, glc_bnd_6.0 and domain_900). Every other arm of the
# suite already ran: submit this instead of run_sensitivity_slurm.sh so nothing
# is repeated. Same replicates, seeds and pairing as the stored plan (shared
# pairing: replicate r keeps the seed it had in the first campaign).
#
# From the repository root, one job per new arm (they run concurrently):
#   for f in oxygen_consumption glucose_boundary relative_tumor_size; do
#       sbatch run_sensitivity_new_arms_slurm.sh "opencellcomms_adapters/MicroC/workflows/sensitivity_analysis/p53_sa_$f.json"
#   done
# or all three new arms sequentially in one job:
#   sbatch run_sensitivity_new_arms_slurm.sh
# Each job writes its own runs/<name>_<timestamp> folder;
# collect_sensitivity_results.py picks them up with the earlier batches.

set -euo pipefail
REPO_ROOT="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
VENV="${MICROC_VENV:-$REPO_ROOT/.venv-hpc}"
PYTHON="${MICROC_PYTHON:-$VENV/bin/python}"
SUITE_DIR="${MICROC_SA_DIR:-$REPO_ROOT/opencellcomms_adapters/MicroC/workflows/sensitivity_analysis}"
RUNS_DIR="${MICROC_RUNS_DIR:-$REPO_ROOT/runs}"
RUNNER="$REPO_ROOT/opencellcomms_engine/tools/run_planner_batch.py"

# suite file -> the one Planner tab of that file that has not run yet
NEW_ARMS=(
    "p53_sa_oxygen_consumption.json=o2_cons_6.6"
    "p53_sa_glucose_boundary.json=glc_bnd_6.0"
    "p53_sa_relative_tumor_size.json=domain_900"
)

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
    echo "Pass one suite workflow JSON to run its new arm alone, or nothing to run all new arms; the arms are listed in this script." >&2
    exit 2
}
[ -z "${SLURM_ARRAY_TASK_ID:-}" ] || {
    echo "Submit this as one job, without --array. Replication is already in the workflow plan." >&2
    exit 2
}

if [ "$#" -eq 1 ]; then
    for arm in "${NEW_ARMS[@]}"; do
        if [ "${arm%%=*}" = "$(basename "$1")" ]; then
            exec "$PYTHON" "$RUNNER" --workflow "$1" --tab "${arm#*=}" --runs-dir "$RUNS_DIR"
        fi
    done
    echo "$(basename "$1") has no new arm; the new arms are: ${NEW_ARMS[*]}" >&2
    exit 2
fi
for arm in "${NEW_ARMS[@]}"; do
    "$PYTHON" "$RUNNER" --workflow "$SUITE_DIR/${arm%%=*}" --tab "${arm#*=}" --runs-dir "$RUNS_DIR"
done

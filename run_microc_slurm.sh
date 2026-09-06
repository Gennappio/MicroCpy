#!/bin/bash
#SBATCH --job-name="microc_p53wt"
#SBATCH --mem=80000
#SBATCH --account=abbruzzese
#SBATCH --partition=medium_gpunew
#SBATCH --output=slurm_logs/%x_%j.out
#SBATCH --error=slurm_logs/%x_%j.err
#SBATCH --mail-type=END
#SBATCH --mail-user=gennaro.abbruzzese@unibocconi.it
#SBATCH --cpus-per-task=8

#
# Install the engine (once) and run a MicroC workflow headless.
#
#   mkdir -p slurm_logs      # SLURM will not create the log dir for you
#
#   sbatch run_microc_slurm.sh            # every enabled Planner tab, as the GUI does
#   sbatch run_microc_slurm.sh p53on      # one named arm
#   MICROC_EXTRA_ARGS=--no-observability sbatch run_microc_slurm.sh   # extra run_workflow.py flags
#
# run_sensitivity_slurm.sh runs the full sensitivity suite using the same venv.
# This file supplies its one-time environment setup through --install-only.
#
# Planner runs retain separate configuration/replicate/attempt folders under
# runs/, including the exact workflow and seed. Results are never mixed.
#
# NO GPU IS REQUESTED. MicroC solves diffusion with FiPy on top of
# numpy/scipy; there is no CUDA path anywhere in the engine, so the template's
# `--gpus=4` would reserve four idle cards and queue longer for nothing. If the
# `gpu` partition on this cluster refuses jobs that request no GPU, either add
# `#SBATCH --gpus=1` back or submit elsewhere:
#   sbatch --partition=<cpu_partition> run_microc_slurm.sh

set -euo pipefail

# --------------------------------------------------------------------------
# Configuration -- override any of these from the environment at submit time,
#   MICROC_WORKFLOW=.../microc.json sbatch run_microc_slurm.sh
# --------------------------------------------------------------------------
REPO_ROOT="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
WORKFLOW="${MICROC_WORKFLOW:-$REPO_ROOT/opencellcomms_adapters/MicroC/workflows/microc_p53_experiment.json}"
VENV="${MICROC_VENV:-$REPO_ROOT/.venv-hpc}"
PYTHON="${MICROC_PYTHON:-python3}"
ARM="${1:-${MICROC_ARM:-}}"
EXTRA_ARGS="${MICROC_EXTRA_ARGS:-}"   # appended verbatim to run_workflow.py, e.g. --no-observability

# Cluster-specific. Uncomment and adapt if python3 is not on PATH by default.
# module load python/3.11

cd "$REPO_ROOT"
mkdir -p slurm_logs

echo "start"
echo "  host      : $(hostname)"
echo "  repo      : $REPO_ROOT"
echo "  workflow  : $WORKFLOW"
echo "  arm       : ${ARM:-<all enabled Planner tabs>}"
echo "  extra     : ${EXTRA_ARGS:-<none>}"
echo "  job       : ${SLURM_JOB_ID:-<interactive>}"

[ -f "$WORKFLOW" ] || { echo "ERROR: workflow not found: $WORKFLOW" >&2; exit 1; }

# --------------------------------------------------------------------------
# Install. Idempotent: the venv is built and populated on the first run only,
# so resubmitting does not reinstall. Delete $VENV to force a rebuild, or
# prebuild it with:  bash run_microc_slurm.sh --install-only
# --------------------------------------------------------------------------
if [ ! -d "$VENV" ]; then
    echo "[install] creating venv at $VENV"
    "$PYTHON" -m venv "$VENV"
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    pip install --quiet --upgrade pip
    # [diffusion] pulls FiPy, which the coupled solver this workflow uses needs.
    # Add ,maboss only for workflows whose gene update is step_maboss; the p53
    # workflows use the single-gene NetLogo update and do not need it.
    echo "[install] installing engine (this takes a few minutes)"
    pip install --quiet -e "$REPO_ROOT/opencellcomms_engine[diffusion]"
else
    echo "[install] reusing venv at $VENV"
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
fi

python -c "import fipy, numpy, matplotlib" \
    || { echo "ERROR: engine dependencies missing — delete $VENV and resubmit" >&2; exit 1; }

if [ "$ARM" = "--install-only" ]; then
    echo "[install] done; venv ready at $VENV"
    exit 0
fi

# Headless: no display on a compute node, and keep BLAS from oversubscribing
# the cores SLURM actually gave us.
export MPLBACKEND=Agg
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-1}"
export OPENBLAS_NUM_THREADS="$OMP_NUM_THREADS"
export MKL_NUM_THREADS="$OMP_NUM_THREADS"

# --------------------------------------------------------------------------
# Run. The engine expands the Planner itself -- a workflow carrying enabled
# tabs runs one experiment per tab, exactly as it does in the GUI -- so there
# is nothing to orchestrate here. Pass an arm name to run just one.
#
# Executed from the engine directory because a workflow's relative paths
# (e.g. ../data/initial_cells_500_center_1500.csv) resolve against the
# workflow file, and results land under the engine tree.
# --------------------------------------------------------------------------
cd "$REPO_ROOT/opencellcomms_engine"
# shellcheck disable=SC2086  # EXTRA_ARGS is a list of flags, split on purpose
if [ -n "$ARM" ]; then
    python run_workflow.py --workflow "$WORKFLOW" --planner-tab "$ARM" $EXTRA_ARGS
else
    python run_workflow.py --workflow "$WORKFLOW" $EXTRA_ARGS
fi

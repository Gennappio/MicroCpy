"""Exercise the single-file SLURM entry point locally, without submitting jobs."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.workflow import replication


REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / 'run_sensitivity_slurm.sh'
RUNNER = REPO / 'opencellcomms_engine/tools/run_planner_batch.py'
SUITE = REPO / 'opencellcomms_adapters/MicroC/workflows/sensitivity_analysis'


def job_env(**overrides):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('SLURM_', 'MICROC_'))}
    env.update(SLURM_SUBMIT_DIR=str(REPO), SLURM_JOB_ID='local-test',
               SLURM_CPUS_PER_TASK='2', MICROC_PYTHON=sys.executable)
    env.update(overrides)
    return env


def launch(args=(), env=None):
    return subprocess.run(['bash', str(SCRIPT), *map(str, args)], cwd=REPO,
                          env=env or job_env(), capture_output=True, text=True, timeout=90)


@pytest.fixture
def capture_python(tmp_path):
    python = tmp_path / 'capture-python'
    python.write_text('#!' + sys.executable + '\n' +
        'import json, os, sys\n'
        'print(json.dumps({"args": sys.argv[1:], "threads": '
        '[os.environ[k] for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")]}))\n')
    python.chmod(0o755)
    return job_env(MICROC_PYTHON=str(python), MICROC_THREADS='8')


def test_plain_submission_runs_whole_suite_and_honours_allocated_cpus(capture_python):
    result = launch(env=capture_python)
    assert result.returncode == 0, result.stderr
    captured = json.loads(result.stdout)
    assert captured['args'] == [str(RUNNER), '--suite', str(SUITE)]
    assert captured['threads'] == ['2', '2', '2']
    flags = ['--replicates', '7', '--master-seed', '123']
    result = launch(flags, capture_python)
    assert json.loads(result.stdout)['args'][-4:] == flags


@pytest.mark.parametrize('index', [None, '3'])
def test_saved_plan_supports_whole_job_or_one_array_worker(tmp_path, capture_python, index):
    manifest = tmp_path / 'saved plan.json'
    manifest.write_text('{}')
    if index is not None:
        capture_python['SLURM_ARRAY_TASK_ID'] = index
    result = launch([manifest], capture_python)
    assert result.returncode == 0, result.stderr
    expected = [str(RUNNER), '--manifest', str(manifest)]
    if index is not None:
        expected += ['--index', index]
    assert json.loads(result.stdout)['args'] == expected


def test_array_without_saved_plan_does_not_duplicate_the_suite(capture_python):
    capture_python['SLURM_ARRAY_TASK_ID'] = '0'
    result = launch(['--replicates', '2'], capture_python)
    assert result.returncode != 0
    assert 'Array jobs require a saved manifest' in result.stderr
    assert result.stdout == ''


def test_real_full_suite_plan_includes_all_axes_seeds_and_separate_folders(tmp_path):
    # The default execution path can prepare the real suite without a long run.
    result = launch(['--replicates', '2', '--master-seed', '123',
                     '--runs-dir', tmp_path, '--prepare'])
    assert result.returncode == 0, result.stdout + result.stderr
    manifests = list(tmp_path.glob('*/manifest.json'))
    assert len(manifests) == 1
    plan = replication.read_json(manifests[0])
    assert {Path(request['source']).name for request in plan['requests']} == \
        {path.name for path in SUITE.glob('p53_sa_*.json')}
    assert len(plan['requests']) == 15
    assert len(plan['configurations']) == 12
    assert plan['requested_runs'] == 30 and plan['unique_runs'] == 24
    assert len({run['seed'] for run in plan['runs']}) == 2
    assert len({run['output_dir'] for run in plan['runs']}) == 24
    for config in plan['configurations']:
        frozen = replication.read_json(manifests[0].parent / config['workflow_file'])
        assert any(node['function_name'] == 'record_lactate_balance'
                   for node in frozen['subworkflows']['diffusion_step']['functions'])


def test_single_job_executes_all_replicates_and_resume_preserves_results(tmp_path):
    suite = tmp_path / 'suite'
    suite.mkdir()
    for name in ('First', 'Second'):
        # Minimal executable workflows test dispatch, not biological behaviour.
        replication.write_json(suite / f'p53_sa_{name}.json', {
            'version': '2.0', 'name': name, 'metadata': {'smoke_case': name},
            'subworkflows': {'main': {'functions': [], 'deletable': False}},
        })
    env = job_env(MICROC_SA_DIR=str(suite))
    result = launch(['--replicates', '2', '--master-seed', '123',
                     '--runs-dir', tmp_path / 'runs'], env)
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = next((tmp_path / 'runs').glob('*/manifest.json'))
    batch = manifest.parent
    state = replication.batch_status(batch)
    assert state['completed'] == state['unique_runs'] == 4
    paths = [batch / run['attempt_dir'] / 'workflow.json' for run in state['runs']]
    assert len(set(paths)) == 4
    originals = {path: path.read_bytes() for path in paths}
    result = launch([manifest], env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert all(len(run['attempts']) == 1 for run in replication.batch_status(batch)['runs'])
    assert all(path.read_bytes() == contents for path, contents in originals.items())

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
                          env=env or job_env(), capture_output=True, text=True,
                          timeout=90)


@pytest.fixture
def capture_python(tmp_path):
    python = tmp_path / 'capture-python'
    python.write_text('#!' + sys.executable + '\n' +
        'import json, os, sys\n'
        'print(json.dumps({"args": sys.argv[1:], "threads": '
        '[os.environ[k] for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")]}))\n')
    python.chmod(0o755)
    return job_env(MICROC_PYTHON=str(python), MICROC_THREADS='8')


def test_plain_submission_reads_only_workflows_and_honours_allocated_cpus(capture_python):
    result = launch(env=capture_python)
    assert result.returncode == 0, result.stderr
    captured = json.loads(result.stdout)
    assert captured['args'] == [str(RUNNER), '--suite', str(SUITE),
                                '--runs-dir', str(REPO / 'runs')]
    assert captured['threads'] == ['2', '2', '2']


def test_launcher_rejects_plan_arguments(capture_python):
    result = launch(['--replicates', '2'], capture_python)
    assert result.returncode == 2
    assert 'takes no arguments' in result.stderr
    assert result.stdout == ''


def test_launcher_rejects_arrays(capture_python):
    capture_python['SLURM_ARRAY_TASK_ID'] = '0'
    result = launch(env=capture_python)
    assert result.returncode == 2
    assert 'without --array' in result.stderr
    assert result.stdout == ''


def test_full_suite_plan_comes_from_workflows_and_has_separate_folders(tmp_path):
    paths = sorted(SUITE.glob('p53_sa_*.json'))
    documents = [{'workflow': replication.read_json(path), 'source': str(path)}
                 for path in paths]
    settings = {json.dumps(doc['workflow']['metadata']['gui']['planner']['replication'],
                           sort_keys=True) for doc in documents}
    assert settings == {json.dumps({
        'replicates': 10, 'seedMode': 'generated', 'masterSeed': '42',
        'pairing': 'shared', 'pairingGroup': 'default', 'seeds': [],
    }, sort_keys=True)}

    plan = replication.compile_plan(documents)
    assert {Path(request['source']).name for request in plan['requests']} == \
        {path.name for path in paths}
    assert len(plan['requests']) == 15
    assert len(plan['configurations']) == 12
    assert plan['requested_runs'] == 150
    assert plan['unique_runs'] == 120
    assert len({run['seed'] for run in plan['runs']}) == 10

    batch = replication.create_batch(documents, tmp_path, plan)
    receipt = replication.read_json(batch / 'manifest.json')
    assert len({run['output_dir'] for run in receipt['runs']}) == 120
    assert not list(batch.glob('plan-*.json'))
    for config in receipt['configurations']:
        frozen = replication.read_json(batch / config['workflow_file'])
        assert frozen['metadata']['gui']['planner']['replication']['replicates'] == 10
        assert any(node['function_name'] == 'record_lactate_balance'
                   for node in frozen['subworkflows']['diffusion_step']['functions'])


def test_one_launcher_process_executes_every_workflow_replicate(tmp_path):
    suite = tmp_path / 'suite'
    suite.mkdir()
    replication_block = {
        'replicates': 2, 'seedMode': 'generated', 'masterSeed': '123',
        'pairing': 'shared', 'pairingGroup': 'default', 'seeds': [],
    }
    for index, name in enumerate(('First', 'Second'), 1):
        replication.write_json(suite / f'p53_sa_{name}.json', {
            'version': '2.0', 'name': name,
            'subworkflows': {'main': {'functions': [], 'deletable': False,
                'parameters': [{'id': 'condition', 'parameters': {'value': index}}]}},
            'metadata': {'gui': {'planner': {'version': 2,
                'replication': replication_block,
                'tabs': [{'id': name.lower(), 'name': name, 'enabled': True,
                          'parameterOverrides': {}}]}}},
        })
    runs = tmp_path / 'runs'
    env = job_env(MICROC_SA_DIR=str(suite), MICROC_RUNS_DIR=str(runs))
    result = launch(env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    receipts = list(runs.glob('*/manifest.json'))
    assert len(receipts) == 1
    batch = receipts[0].parent
    state = replication.batch_status(batch)
    assert state['requested_runs'] == state['unique_runs'] == state['completed'] == 4
    assert len({run['attempt_dir'] for run in state['runs']}) == 4
    assert not list(batch.glob('plan-*.json'))
    for run in state['runs']:
        executed = replication.read_json(batch / run['attempt_dir'] / 'workflow.json')
        assert executed['metadata']['gui']['planner']['replication'] == replication_block

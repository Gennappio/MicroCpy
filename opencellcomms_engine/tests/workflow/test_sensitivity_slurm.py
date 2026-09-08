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
NEW_ARMS_SCRIPT = REPO / 'run_sensitivity_new_arms_slurm.sh'
NEW_ARMS = {'p53_sa_oxygen_consumption.json': 'o2_cons_6.6',
            'p53_sa_glucose_boundary.json': 'glc_bnd_6.0',
            'p53_sa_relative_tumor_size.json': 'domain_900'}
RUNNER = REPO / 'opencellcomms_engine/tools/run_planner_batch.py'
SUITE = REPO / 'opencellcomms_adapters/MicroC/workflows/sensitivity_analysis'


def job_env(**overrides):
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(('SLURM_', 'MICROC_'))}
    env.update(SLURM_SUBMIT_DIR=str(REPO), SLURM_JOB_ID='local-test',
               SLURM_CPUS_PER_TASK='2', MICROC_PYTHON=sys.executable)
    env.update(overrides)
    return env


def launch(args=(), env=None, script=SCRIPT):
    return subprocess.run(['bash', str(script), *map(str, args)], cwd=REPO,
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


def test_single_workflow_submission_runs_that_file_alone(capture_python):
    workflow = SUITE / 'p53_sa_oxygen_consumption.json'
    result = launch([workflow], capture_python)
    assert result.returncode == 0, result.stderr
    captured = json.loads(result.stdout)
    assert captured['args'] == [str(RUNNER), '--workflow', str(workflow),
                                '--runs-dir', str(REPO / 'runs')]


def test_launcher_rejects_plan_arguments(capture_python):
    result = launch(['--replicates', '2'], capture_python)
    assert result.returncode == 2
    assert 'the plan itself comes from the workflow files' in result.stderr
    assert result.stdout == ''


def test_launcher_rejects_arrays(capture_python):
    capture_python['SLURM_ARRAY_TASK_ID'] = '0'
    result = launch(env=capture_python)
    assert result.returncode == 2
    assert 'without --array' in result.stderr
    assert result.stdout == ''


def test_new_arms_launcher_runs_only_the_replacement_tabs(capture_python):
    result = launch(env=capture_python, script=NEW_ARMS_SCRIPT)
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line)['args'] for line in result.stdout.splitlines()]
    assert calls == [[str(RUNNER), '--workflow', str(SUITE / name), '--tab', tab,
                      '--runs-dir', str(REPO / 'runs')] for name, tab in NEW_ARMS.items()]

    workflow = SUITE / 'p53_sa_glucose_boundary.json'
    result = launch([workflow], capture_python, script=NEW_ARMS_SCRIPT)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['args'] == [
        str(RUNNER), '--workflow', str(workflow), '--tab', 'glc_bnd_6.0',
        '--runs-dir', str(REPO / 'runs')]

    result = launch([SUITE / 'p53_sa_propagation_steps.json'], capture_python, script=NEW_ARMS_SCRIPT)
    assert result.returncode == 2
    assert 'has no new arm' in result.stderr
    assert result.stdout == ''


def test_tab_filter_keeps_a_subset_of_the_stored_plan_with_the_same_seeds():
    paths = sorted(SUITE.glob('p53_sa_*.json'))
    documents = [{'workflow': replication.read_json(path), 'source': str(path)}
                 for path in paths]
    full = replication.compile_plan(documents)
    subset = replication.compile_plan(documents, tab_names=list(NEW_ARMS.values()))
    assert [r['name'] for r in subset['requests']] == ['glc_bnd_6.0', 'o2_cons_6.6', 'domain_900']
    assert subset['requested_runs'] == subset['unique_runs'] == 30
    assert {r['seed'] for r in subset['runs']} == {r['seed'] for r in full['runs']}
    assert {c['id'] for c in subset['configurations']} <= {c['id'] for c in full['configurations']}
    assert {r['id'] for r in subset['runs']} <= {r['id'] for r in full['runs']}
    with pytest.raises(ValueError, match='o2_cons_13.2'):
        replication.compile_plan(documents, tab_names=['o2_cons_6.6', 'o2_cons_13.2'])


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

    # The override-free baseline tab is enabled in one file only, so separate
    # per-file jobs never repeat it: 12 requests, 120 runs, no duplicates.
    baseline_tabs = {path.name: [tab['name'] for tab in
                                 doc['workflow']['metadata']['gui']['planner']['tabs']
                                 if not tab['parameterOverrides']]
                     for path, doc in zip(paths, documents)}
    enabled_baselines = {path.name: [tab['name'] for tab in
                                     doc['workflow']['metadata']['gui']['planner']['tabs']
                                     if not tab['parameterOverrides'] and tab['enabled']]
                         for path, doc in zip(paths, documents)}
    assert sum(map(len, baseline_tabs.values())) == 4
    assert enabled_baselines['p53_sa_glucose_boundary.json'] == ['glc_bnd_5.0']
    assert sum(map(len, enabled_baselines.values())) == 1
    per_file = [replication.compile_plan([doc])['unique_runs'] for doc in documents]
    assert sum(per_file) == 120

    plan = replication.compile_plan(documents)
    assert {Path(request['source']).name for request in plan['requests']} == \
        {path.name for path in paths}
    assert len(plan['requests']) == 12
    assert len(plan['configurations']) == 12
    assert plan['requested_runs'] == 120
    assert plan['unique_runs'] == 120
    assert len({run['seed'] for run in plan['runs']}) == 10

    batch = replication.create_batch(documents, tmp_path, plan)
    receipt = replication.read_execution_record(batch)
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
    batches = [path for path in runs.iterdir()
               if path.is_dir() and replication.execution_record_path(path).is_file()]
    assert len(batches) == 1
    batch = batches[0]
    state = replication.batch_status(batch)
    assert state['requested_runs'] == state['unique_runs'] == state['completed'] == 4
    assert len({run['attempt_dir'] for run in state['runs']}) == 4
    assert not list(batch.glob('plan-*.json'))
    for run in state['runs']:
        executed = replication.read_json(batch / run['attempt_dir'] / 'workflow.json')
        assert executed['metadata']['gui']['planner']['replication'] == replication_block


def fabricate_completed_batch(path, runs_dir):
    """Create a batch for one suite file and fake every replicate's outputs."""
    documents = [{'workflow': replication.read_json(path), 'source': str(path)}]
    batch = replication.create_batch(documents, runs_dir)
    manifest = replication.read_execution_record(batch)
    for run in manifest['runs']:
        config = next(c for c in manifest['configurations'] if c['id'] == run['configuration_id'])
        attempt = replication.run_directory(batch, run)
        attempt.mkdir(parents=True)
        workflow = replication.read_json(batch / config['workflow_file'])
        workflow['metadata']['replicate'] = {**run, 'batch_id': manifest['batch_id']}
        replication.write_json(attempt / 'workflow.json', workflow)
        replication.write_json(attempt / 'execution.json',
                               {'status': 'completed', 'numerical_valid': True, 'seed': run['seed']})
        replication.write_json(attempt / 'status.json',
                               {'status': 'completed', 'numerical_valid': True})
        series = attempt / 'sensitivity_summary' / 'timeseries'
        series.mkdir(parents=True)
        (series / 'sensitivity_metrics_over_time.csv').write_text(
            'iteration,tumor_radius_um,relative_tumor_size,viable_cells\n'
            '1,276.6,0.369,1000\n2,280.0,0.373,1010\n')
    return batch


def test_collector_reports_the_single_baseline_on_every_axis(tmp_path):
    runs = tmp_path / 'runs'
    owner = fabricate_completed_batch(SUITE / 'p53_sa_glucose_boundary.json', runs)
    fabricate_completed_batch(SUITE / 'p53_sa_oxygen_consumption.json', runs)
    out = tmp_path / 'summary.csv'
    result = subprocess.run([sys.executable, str(SUITE / 'collect_sensitivity_results.py'),
                             '--runs', str(runs), '--out', str(out)],
                            cwd=REPO, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    import csv
    with out.open(newline='') as stream:
        rows = list(csv.DictReader(stream))

    manifest = replication.read_execution_record(owner)
    baseline = next(r['configuration_id'] for r in manifest['requests'] if r['name'] == 'glc_bnd_5.0')
    baseline_ids = {r['id'] for r in manifest['runs'] if r['configuration_id'] == baseline}
    assert len(baseline_ids) == 10

    by_axis = {}
    for row in rows:
        by_axis.setdefault(row['axis'], []).append(row)
    # 20 sweep rows + 10 baseline rows on the owning axis; 20 on oxygen plus the
    # same 10 baseline runs; the baseline alone on the two axes without a job.
    assert {axis: len(items) for axis, items in by_axis.items()} == {
        'glucose_boundary': 30, 'oxygen_consumption': 30,
        'glucose_consumption': 10, 'relative_tumor_size': 10}
    assert len(rows) == len({(row['run_id'], row['axis']) for row in rows})
    for axis, level in (('glucose_boundary', '5.0'), ('oxygen_consumption', '11'),
                        ('glucose_consumption', '7'), ('relative_tumor_size', '0.369')):
        levels = {row['level'] for row in by_axis[axis] if row['run_id'] in baseline_ids}
        assert levels == {level}, (axis, levels)
        assert {row['run_id'] for row in by_axis[axis] if row['level'] == level} == baseline_ids
    assert 'propagation_steps' not in by_axis

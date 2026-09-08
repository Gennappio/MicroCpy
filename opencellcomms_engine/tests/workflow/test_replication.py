"""Scientific run identities, frozen inputs, retry semantics and valid n."""
import copy
import json
import random
import tarfile
from pathlib import Path

import numpy as np
import pytest
from src.workflow import replication as r
from src.workflow.randomness import seed_run

REPO = Path(__file__).resolve().parents[3]
SUITE = REPO / 'opencellcomms_adapters/MicroC/workflows/sensitivity_analysis'


def workflow(count=3):
    return {'name': 'Test', 'version': '2.0', 'seed': 42, 'subworkflows': {
        'main': {'functions': [], 'parameters': [{'id': 'p', 'parameters': {'name': 'oxygen', 'value': 1}}]}},
        'metadata': {'gui': {'planner': {'version': 2, 'replication': {
            'replicates': count, 'masterSeed': '1357'}, 'tabs': [
            {'id': 'base', 'name': 'Reference', 'enabled': True, 'role': 'reference', 'parameterOverrides': {}},
            {'id': 'other', 'name': 'Changed', 'enabled': True, 'parameterOverrides': {'p': {'parameters': {'name': 'oxygen', 'value': 2}}}},
        ]}}}}


def plan(doc):
    return r.compile_plan([{'workflow': doc}])


def seeds(planned):
    return {(x['configuration_id'], x['replicate']): x['seed'] for x in planned['runs']}


def test_stable_identity_pairing_and_workflow_owned_plan(tmp_path):
    doc = workflow()
    original = plan(doc)
    assert len({x['seed'] for x in original['runs']}) == 3
    doc['name'] = 'Renamed'
    tabs = doc['metadata']['gui']['planner']['tabs']
    tabs.reverse()
    tabs[0]['name'] = 'Renamed tab'
    assert seeds(plan(doc)) == seeds(original)
    batch = r.create_batch([], tmp_path, original)
    receipt = r.read_execution_record(batch)
    assert len(receipt['runs']) == 6
    assert not list(batch.glob('plan-*.json'))
    for config in receipt['configurations']:
        frozen = r.read_json(batch / config['workflow_file'])
        planned = next(item for item in original['configurations'] if item['id'] == config['id'])
        assert frozen['metadata']['gui']['planner'] == planned['workflow']['metadata']['gui']['planner']
    assert not (batch / 'manifest.json').exists()
    assert not (batch / 'source.tar.gz').exists()
    assert not (batch / 'working-tree.patch').exists()
    assert r.execution_record_path(batch) == batch / '.opencellcomms/execution.json'
    archive_path = batch / '.opencellcomms/source.tar.gz'
    assert archive_path.is_file()
    with tarfile.open(archive_path) as archive:
        assert 'opencellcomms_engine/src/workflow/replication.py' in archive.getnames()


def test_independent_seeds_use_persistent_ids():
    doc = workflow()
    doc['metadata']['gui']['planner']['replication']['pairing'] = 'independent'
    original = plan(doc)
    assert len({x['seed'] for x in original['runs']}) == 6
    doc['metadata']['gui']['planner']['tabs'].reverse()
    assert seeds(plan(doc)) == seeds(original)


def test_readable_folders_are_unique_and_do_not_change_seeds(tmp_path, monkeypatch):
    class FixedDateTime(r.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 6, 15, 30, 0, tzinfo=tz)
    monkeypatch.setattr(r, 'datetime', FixedDateTime)
    doc = workflow(2)
    tabs = doc['metadata']['gui']['planner']['tabs']
    tabs[0]['name'], tabs[1]['name'] = 'Dose / 5.0', 'dose : 5.0'
    original = plan(doc)
    batch = r.create_batch([], tmp_path, original)
    assert batch.name == 'Test_2026-09-06_15-30-00'
    saved = r.read_execution_record(batch)
    assert seeds(saved) == seeds(original)
    assert [c['output_folder'] for c in saved['configurations']] == ['Dose_5.0', 'dose_5.0_2']
    assert saved['runs'][0]['output_dir'] == 'Dose_5.0/replicate-001'
    assert saved['runs'][1]['output_dir'] == 'Dose_5.0/replicate-002'
    assert (batch / '.opencellcomms/workflows/Dose_5.0.json').is_file()
    completed(batch, saved['runs'][0], 1, 7)
    assert (batch / 'Dose_5.0/replicate-001/status.json').is_file()
    assert not list(batch.glob('*/replicate-*/attempt-*'))
    before = r.execution_record_path(batch).read_bytes()
    second = r.create_batch([], tmp_path, original)
    assert second.name == batch.name + '_2'
    assert r.execution_record_path(batch).read_bytes() == before
    assert r.run_status(batch, saved['runs'][0])['status'] == 'completed'


def test_independent_duplicate_configs_keep_separate_folders(tmp_path):
    doc = workflow(2)
    doc['metadata']['gui']['planner']['replication']['pairing'] = 'independent'
    doc['metadata']['gui']['planner']['tabs'][1]['parameterOverrides'] = {}
    batch = r.create_batch([{'workflow': doc}], tmp_path)
    original = r.read_execution_record(batch)['runs']
    assert len(original) == 4
    assert len({run['output_dir'] for run in original}) == 4
    assert len({run['seed'] for run in original}) == 4
    assert [run['output_dir'] for run in original] == [f'Reference/replicate-{i:03d}' for i in range(1, 5)]


def test_legacy_hash_folders_remain_readable(tmp_path):
    batch = r.create_batch([{'workflow': workflow(1)}], tmp_path)
    saved = r.read_execution_record(batch)
    for config in saved['configurations']:
        config.pop('output_folder')
    for run in saved['runs']:
        run.pop('output_dir')
        run.pop('output_index')
    r.execution_record_path(batch).unlink()
    r.write_json(batch / 'manifest.json', saved)
    first = saved['runs'][0]
    completed(batch, first, 1, 7)
    expected = batch / first['configuration_id'] / first['id'] / 'attempt-001'
    assert (expected / 'status.json').is_file()
    assert r.batch_status(batch)['completed'] == 1
    assert r.run_status(batch, first)['status'] == 'completed'


def test_changing_replicates_requires_a_new_workflow_plan(tmp_path):
    doc = workflow(1)
    first = r.create_batch([{'workflow': doc}], tmp_path)
    first_receipt = r.execution_record_path(first).read_bytes()
    doc['metadata']['gui']['planner']['replication']['replicates'] = 2
    second = r.create_batch([{'workflow': doc}], tmp_path)
    assert r.read_execution_record(first)['requested_runs'] == 2
    assert r.read_execution_record(second)['requested_runs'] == 4
    assert r.execution_record_path(first).read_bytes() == first_receipt
    assert not list(tmp_path.rglob('plan-*.json'))


def test_duplicate_baseline_counts_once_and_biology_name_is_semantic():
    doc = workflow()
    doc['metadata']['gui']['planner']['tabs'].append({'id': 'copy', 'name': 'Copy', 'enabled': True})
    assert plan(doc)['requested_runs'] == 9
    assert plan(doc)['unique_runs'] == 6
    changed = copy.deepcopy(doc)
    changed['subworkflows']['main']['parameters'][0]['parameters']['name'] = 'glucose'
    assert r.semantic_workflow(changed) != r.semantic_workflow(doc)


def test_sensitivity_suite_deduplicates_baselines():
    docs = [{'workflow': r.read_json(p), 'source': str(p)} for p in sorted(SUITE.glob('p53_sa_*.json'))]
    planned = r.compile_plan(docs)
    # The suite files enable the baseline tab in one file only, so nothing is
    # requested twice; the dedup still holds when every baseline tab is on.
    assert planned['requested_runs'] == planned['unique_runs'] == 120
    for doc in docs:
        for tab in doc['workflow']['metadata']['gui']['planner']['tabs']:
            tab['enabled'] = True
    planned = r.compile_plan(docs)
    assert planned['requested_runs'] == 150
    assert planned['unique_runs'] == 120
    assert len({run['seed'] for run in planned['runs']}) == 10


@pytest.mark.parametrize('patch', [
    {'replicates': 0}, {'replicates': 1.5}, {'masterSeed': 'bad'},
    {'seedMode': 'explicit', 'seeds': ['17', '17']},
    {'seedMode': 'explicit', 'seeds': ['0']},
])
def test_invalid_replication_rejected(patch):
    doc = workflow()
    doc['metadata']['gui']['planner']['replication'].update(patch)
    with pytest.raises(ValueError):
        plan(doc)


def test_explicit_large_seeds_and_fresh_resolved_once():
    doc = workflow()
    settings = doc['metadata']['gui']['planner']['replication']
    settings.update(seedMode='explicit', seeds=['9007199254740993', '123'])
    explicit = plan(doc)
    assert {x['seed'] for x in explicit['runs']} == {'9007199254740993', '123'}
    settings.update(seedMode='fresh')
    fresh = r.compile_plan([{'workflow': doc}], fresh_seed=987)
    assert {x['settings']['masterSeed'] for x in fresh['requests']} == {'987'}


def test_all_run_generators_replay_and_vary():
    def draw(seed):
        ctx = {}
        effective = seed_run(ctx, seed)
        return effective, [random.random(), float(np.random.random()), float(ctx['_rng'].random())]
    assert draw(123) == draw(123)
    assert draw(123)[1] != draw(124)[1]
    effective, numbers = draw(0)
    assert effective > 0
    assert draw(effective)[1] == numbers


def test_frozen_inputs_and_workflow_are_immutable(tmp_path, monkeypatch):
    monkeypatch.setattr(r, 'REPO', tmp_path)
    # Resolver is imported from the real engine but the input is an absolute path.
    source = tmp_path / 'data.csv'
    source.write_text('x,y\n1,2\n')
    doc = workflow(1)
    doc['subworkflows']['main']['parameters'].append({'id': 'input', 'parameters': {'file_path': str(source)}})
    monkeypatch.setattr(r, 'code_files', lambda: [])
    batch = r.create_batch([{'workflow': doc}], tmp_path / 'runs')
    manifest = r.read_execution_record(batch)
    config = manifest['configurations'][0]
    frozen = r.read_json(batch / config['workflow_file'])
    path = Path(frozen['subworkflows']['main']['parameters'][-1]['parameters']['file_path'])
    source.write_text('changed')
    assert path.read_text() == 'x,y\n1,2\n'
    assert r.digest(frozen) == config['workflow_hash']


def completed(batch, run, attempt, value, valid=True, endpoint='20'):
    parent = r.run_directory(batch, run)
    if r.execution_record_path(batch).parent.name == r.INTERNAL_DIRECTORY:
        folder = parent if attempt == 1 else parent.with_name(parent.name + f'_retry-{attempt:03d}')
    else:
        folder = parent / f'attempt-{attempt:03d}'
    r.write_json(folder / 'status.json', {'status': 'completed', 'numerical_valid': valid,
        'metrics': {'survival': {'value': value, 'endpoint': ['gene_steps', endpoint]}}})


def test_summary_uses_replicates_not_attempts_and_pairs_matching_endpoints(tmp_path):
    batch = r.create_batch([{'workflow': workflow(3)}], tmp_path)
    runs = r.read_execution_record(batch)['runs']
    for i, run in enumerate(runs):
        completed(batch, run, 1, i+1)
    completed(batch, runs[0], 2, 1)  # Replay must not inflate n.
    completed(batch, runs[1], 2, 999, valid=False)  # Keep prior successful attempt.
    result = r.summarize_batch(batch, 'survival')
    assert [g['n'] for g in result['groups']] == [3, 3]
    delta = result['groups'][1]['paired_difference']
    assert delta['n'] == 3
    assert delta['mean'] == 3
    assert delta['ci95'] == [3, 3]
    completed(batch, runs[5], 2, 6, endpoint='30')
    result = r.summarize_batch(batch, 'survival')
    assert result['groups'][1]['mixed_endpoints']
    assert result['groups'][1]['n'] == 0
    assert result['groups'][1]['paired_difference']['n'] == 2


def test_single_replicate_has_no_ci_and_failures_not_pooled(tmp_path):
    batch = r.create_batch([{'workflow': workflow(1)}], tmp_path)
    runs = r.read_execution_record(batch)['runs']
    completed(batch, runs[0], 1, 7)
    completed(batch, runs[1], 1, 9, valid=False)
    result = r.summarize_batch(batch, 'survival')
    assert result['groups'][0]['ci95'] is None
    assert result['groups'][1]['n'] == 0
    assert r.batch_status(batch)['failed'] == 1


def test_continue_retry_and_replay_share_saved_identities(tmp_path, monkeypatch):
    batch = r.create_batch([{'workflow': workflow(1)}], tmp_path)
    runs = r.read_execution_record(batch)['runs']
    completed(batch, runs[0], 1, 7)
    calls = []
    monkeypatch.setattr(r, 'execute_run', lambda batch, run, manifest, **kwargs: calls.append(run['id']) or True)
    r.execute_batch(batch, 'continue')
    assert calls == [runs[1]['id']]
    calls.clear()
    r.execute_batch(batch, 'retry')
    assert not calls  # Planned runs are not failed attempts.
    r.execute_batch(batch, 'replay', runs[0]['id'])
    assert calls == [runs[0]['id']]
    monkeypatch.setattr(r, 'code_fingerprint', lambda: 'changed')
    with pytest.raises(ValueError, match='code changed'):
        r.execute_batch(batch)


def test_gui_biological_routing_is_part_of_configuration_identity():
    doc = workflow()
    changed = copy.deepcopy(doc)
    changed['metadata']['gui']['agent_kinds'] = [{'name': 'cancer', 'class': 'TumorCell'}]
    assert r.semantic_workflow(doc) != r.semantic_workflow(changed)


def test_legacy_zero_means_fresh_and_environment_mismatch_blocks_replay(tmp_path, monkeypatch):
    doc = workflow(1)
    doc['seed'] = 0
    doc['metadata']['gui']['planner'].pop('replication')
    assert r.replication_settings(doc)['seedMode'] == 'fresh'
    batch = r.create_batch([{'workflow': workflow(1)}], tmp_path)
    env = r.environment()
    env['packages']['numpy'] = 'different'
    monkeypatch.setattr(r, 'environment', lambda: env)
    with pytest.raises(ValueError, match='environment'):
        r.execute_batch(batch)


def test_independent_contrast_and_replay_mismatch_remain_visible(tmp_path):
    doc = workflow(3)
    doc['metadata']['gui']['planner']['replication']['pairing'] = 'independent'
    batch = r.create_batch([{'workflow': doc}], tmp_path)
    runs = r.read_execution_record(batch)['runs']
    for i, run in enumerate(runs):
        completed(batch, run, 1, i+1)
    result = r.summarize_batch(batch, 'survival')['groups'][1]
    assert result['paired_difference'] is None
    assert result['independent_difference']['mean'] == 3
    assert result['independent_difference']['ci95'][0] < 3
    first = runs[0]
    parent = r.run_directory(batch, first)
    bad = parent.with_name(parent.name + '_retry-002') / 'status.json'
    r.write_json(bad, {'status': 'completed', 'numerical_valid': True, 'replay_matches': False,
                      'metrics': {'survival': {'value': 999, 'endpoint': ['gene_steps', '20']}}})
    assert r.batch_status(batch)['replay_mismatches'] == 1
    assert r.summarize_batch(batch, 'survival')['groups'][0]['mean'] == 2


@pytest.mark.slow
def test_microc_replay_in_fresh_processes(tmp_path):
    source = SUITE / 'p53_sa_glucose_consumption.json'
    doc = r.read_json(source)
    planner = doc['metadata']['gui']['planner']
    planner['tabs'] = planner['tabs'][:1]
    planner['tabs'][0]['parameterOverrides']['steps_param-__scheduler__'] = {'parameters': {'steps': '3'}}
    planner['tabs'][0]['parameterOverrides']['iteration_plots-param_checkpoint_interval'] = {'parameters': {'interval': '1'}}
    planner['replication'] = {'replicates': 1, 'masterSeed': '572'}
    batch = r.create_batch([{'workflow': doc, 'source': str(source)}], tmp_path)
    assert r.execute_batch(batch) == 0
    original = r.batch_status(batch)['runs'][0]
    assert original['metrics']
    prefix = 'sensitivity_summary/timeseries/sensitivity_metrics_over_time.csv:'
    lactate = {name: original['metrics'][prefix + 'lactate_' + name + '_mol_s']['value']
               for name in ('production', 'consumption', 'balance')}
    assert lactate['balance'] == lactate['production'] - lactate['consumption']
    original_folder = batch / original['attempt_dir']
    assert list(original_folder.glob('*/checkpoints/*.npz'))
    original_files = {str(p.relative_to(original_folder)): p.read_bytes() for p in original_folder.rglob('*') if p.is_file()}
    assert r.execute_batch(batch, 'replay', original['id']) == 0
    replay = r.batch_status(batch)['runs'][0]
    assert replay['replay_matches'] is True
    assert replay['metrics'] == original['metrics']
    assert replay['attempt_dir'] != original['attempt_dir']
    first = batch / original['attempt_dir']
    second = batch / replay['attempt_dir']
    trajectories = list(first.glob('*/timeseries/*.csv'))
    assert trajectories
    for path in trajectories:
        assert path.read_bytes() == (second / path.relative_to(first)).read_bytes()
    assert {str(p.relative_to(original_folder)): p.read_bytes() for p in original_folder.rglob('*') if p.is_file()} == original_files

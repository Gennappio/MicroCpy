"""Planner API executes workflow-owned plans and keeps immutable run records."""
import sys
from pathlib import Path
import pytest
from src.workflow import replication as r

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'opencellcomms_gui/server'))
import api


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'RUNS_DIR', tmp_path / 'runs')
    monkeypatch.setattr(api, 'is_running', False)
    monkeypatch.setattr(api, '_start_planner', lambda *args, **kwargs: None)
    api.app.config.update(TESTING=True)
    return api.app.test_client()


def document():
    return {'version': '2.0', 'name': 'Planner API test', 'subworkflows': {'main': {'functions': [], 'deletable': False}},
        'metadata': {'gui': {'planner': {'version': 2, 'replication': {'replicates': 2},
            'tabs': [{'id': 'a', 'name': 'A', 'enabled': True, 'parameterOverrides': {}}]}}}}


def test_preview_and_submission_use_same_seeds_and_reload_can_read(client):
    doc = document()
    preview = client.post('/api/planner/preview', json={'workflow': doc})
    assert preview.status_code == 200, preview.get_json()
    assert not api.RUNS_DIR.exists()
    created = client.post('/api/planner/batches', json={'workflow': doc})
    assert created.status_code == 201, created.get_json()
    batch_id = created.get_json()['batch_id']
    status = client.get('/api/planner/batches/' + batch_id).get_json()
    assert [x['seed'] for x in status['runs']] == [x['seed'] for x in preview.get_json()['runs']]
    assert client.get('/api/planner/batches').get_json()['batches'][0]['unique_runs'] == 2
    assert (api.RUNS_DIR / batch_id / 'source.tar.gz').exists()
    assert not list((api.RUNS_DIR / batch_id).glob('plan-*.json'))
    second = client.post('/api/planner/batches', json={'workflow': doc}).get_json()
    assert second['batch_id'] != batch_id
    assert (api.RUNS_DIR / batch_id / 'manifest.json').exists()


def test_continue_replay_and_busy_guards(client, monkeypatch):
    created = client.post('/api/planner/batches', json={'workflow': document()}).get_json()
    url = '/api/planner/batches/' + created['batch_id']
    assert client.post(url + '/action', json={'action': 'replay'}).status_code == 400
    initial = client.get(url).get_json()['runs']
    assert client.post(url + '/action', json={'action': 'add', 'replicates': 1}).status_code == 400
    after = client.get(url).get_json()['runs']
    assert after == initial
    monkeypatch.setattr(api, 'is_running', True)
    assert client.post(url + '/action', json={'action': 'continue'}).status_code == 409
    assert client.post('/api/planner/batches', json={'workflow': document()}).status_code == 409


def test_invalid_and_outside_paths_are_rejected(client, tmp_path):
    assert client.post('/api/planner/preview', json={}).status_code == 400
    assert client.get('/api/planner/batches/..').status_code == 400
    doc = document()
    doc['metadata']['gui']['planner']['replication']['masterSeed'] = 'NaN'
    assert client.post('/api/planner/batches', json={'workflow': doc}).status_code == 400
    outside = tmp_path / 'secret.csv'
    outside.write_text('secret')
    doc = document()
    doc['subworkflows']['main']['parameters'] = [{'id': 'p', 'parameters': {'file_path': str(outside)}}]
    assert client.post('/api/planner/preview', json={'workflow': doc}).status_code == 400


def test_export_and_results_keep_attempt_history(client):
    created = client.post('/api/planner/batches', json={'workflow': document()}).get_json()
    batch = api.RUNS_DIR / created['batch_id']
    run = r.read_json(batch / 'manifest.json')['runs'][0]
    for i in (1, 2):
        folder = r.run_directory(batch, run) / f'attempt-{i:03d}'
        r.write_json(folder / 'status.json', {'status': 'completed', 'numerical_valid': True})
    results = client.get('/api/results/list').get_json()['results']
    assert len(results) == 2
    assert results[0]['seed'] == run['seed']
    assert 'Planner API test' in results[0]['name']
    assert '/ A / Replicate 1 / attempt-001' in results[0]['name']
    assert run['id'] not in results[0]['name']
    download = client.get('/api/planner/batches/' + batch.name + '/export')
    assert download.status_code == 200
    assert download.data[:2] == b'PK'


def test_old_results_show_workflow_names_instead_of_hashes(client):
    created = client.post('/api/planner/batches', json={'workflow': document()}).get_json()
    batch = api.RUNS_DIR / created['batch_id']
    saved = r.read_json(batch / 'manifest.json')
    saved.pop('name')
    saved['configurations'][0]['source'] = '/workflows/glucose_boundary.json'
    saved['configurations'][0].pop('output_folder')
    for run in saved['runs']:
        run.pop('output_dir')
        run.pop('output_index')
    r.write_json(batch / 'manifest.json', saved)
    batch = batch.rename(api.RUNS_DIR / '20260906T124930-4925defd')
    run = saved['runs'][0]
    folder = batch / run['configuration_id'] / run['id'] / 'attempt-001'
    r.write_json(folder / 'status.json', {'status': 'completed', 'numerical_valid': True})
    results = client.get('/api/results/list').get_json()['results']
    assert len(results) == 1
    assert 'glucose_boundary' in results[0]['name']
    assert batch.name not in results[0]['name']
    assert run['id'] not in results[0]['name']


def test_repeated_gui_labels_preserve_separate_folders_and_prior_results(client, monkeypatch):
    old = api.RUNS_DIR / 'same_label'
    old.mkdir(parents=True)
    (old / 'result.csv').write_text('original result\n')
    unrelated = api.RUNS_DIR / 'earlier_experiment'
    unrelated.mkdir()
    (unrelated / 'result.csv').write_text('earlier result\n')
    monkeypatch.setattr(api, 'run_simulation_async', lambda *args, **kwargs: None)
    paths = []
    for _ in range(2):
        monkeypatch.setattr(api, 'is_running', False)
        response = client.post('/api/run', json={'workflow': document(),
            'run_label': 'same_label', 'keep_labels': ['same_label']})
        assert response.status_code == 200, response.get_json()
        api.simulation_thread.join(timeout=2)
        paths.append(Path(response.get_json()['workflow']).parent)
    assert paths[0] != paths[1]
    assert [p.name for p in paths] == ['same_label_2', 'same_label_3']
    assert all(p.is_dir() and p != old for p in paths)
    assert (old / 'result.csv').read_text() == 'original result\n'
    assert (unrelated / 'result.csv').read_text() == 'earlier result\n'

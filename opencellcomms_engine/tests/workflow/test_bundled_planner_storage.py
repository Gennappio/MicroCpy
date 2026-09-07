"""Bundled scientific workflows keep their complete Planner definition in JSON."""
import json
from pathlib import Path

import pytest

from src.workflow.replication import compile_plan, replication_settings


REPO = Path(__file__).resolve().parents[3]
ADAPTERS = ('SUGARSCAPE', 'TCELL_CORRAL', 'MicroC')
WORKFLOWS = [
    path
    for adapter in ADAPTERS
    for path in sorted((REPO / 'opencellcomms_adapters' / adapter / 'workflows').rglob('*.json'))
]
REPLICATION_KEYS = {
    'replicates', 'seedMode', 'masterSeed', 'pairing', 'pairingGroup', 'seeds',
}


@pytest.mark.parametrize('path', WORKFLOWS,
                         ids=lambda path: str(path.relative_to(REPO)))
def test_bundled_workflow_owns_complete_planner(path):
    workflow = json.loads(path.read_text(encoding='utf-8'))
    planner = workflow['metadata']['gui']['planner']
    assert planner['version'] == 2
    assert REPLICATION_KEYS <= planner['replication'].keys()
    replication_settings(workflow)

    tabs = planner['tabs']
    assert tabs
    ids = [tab['id'] for tab in tabs]
    assert all(ids) and len(ids) == len(set(ids))
    for tab in tabs:
        assert isinstance(tab['name'], str) and tab['name'].strip()
        assert isinstance(tab['enabled'], bool)
        assert isinstance(tab.get('parameterOverrides', {}), dict)

    plan = compile_plan([{'workflow': workflow, 'source': str(path)}])
    assert plan['requested_runs'] >= 1
    assert plan['unique_runs'] >= 1

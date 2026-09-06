import assert from 'node:assert/strict';

// An old browser snapshot must not select a project when the app opens.
const previousSnapshot = JSON.stringify({ version: 1, state: {
  workflow: { name: 'MicroC', subworkflows: { main: { functions: [] } } },
  workflowFilePath: 'microc.json', currentMainTab: 'planner',
  plannerTabs: [{ id: 'previous', name: 'Previous configuration' }],
} });
const storage = new Map([['opencellcomms-workflow', previousSnapshot]]);
const events = new Map();
globalThis.window = {
  addEventListener: (name, handler) => events.set(name, handler),
  localStorage: {
    getItem: (key) => storage.get(key) || null,
    setItem: (key, value) => storage.set(key, value),
    removeItem: (key) => storage.delete(key),
  },
};
const { default: store } = await import('../src/store/workflowStore.js');
const get = store.getState;
assert.equal(get().workflow.name, 'Untitled Workflow');
assert.equal(get().workflowFilePath, null);
assert.equal(get().currentMainTab, 'world');
assert.deepEqual(get().plannerTabs, []);
assert.ok(Object.values(get().stageNodes).every((nodes) => nodes.length === 0));
get().setWorkflowMetadata({ name: 'Chosen project' });
get().addPlannerTab();
const id = get().plannerTabs[0].id;
get().updatePlannerReplication({ replicates: 7, seedMode: 'explicit', seeds: ['9007199254740993', '42'], pairing: 'shared' });
get().setPlannerTabReplication(id, 1);
get().setPlannerReference(id);
const exported = get().exportWorkflow();
assert.equal(exported.metadata.gui.planner.version, 2);
assert.deepEqual(exported.metadata.gui.planner.replication.seeds, ['9007199254740993', '42']);
get().clearWorkflow();
get().loadWorkflow(exported, 'chosen-project.json');
assert.equal(get().workflow.name, 'Chosen project');
assert.equal(get().workflowFilePath, 'chosen-project.json');
assert.equal(get().plannerTabs[0].id, id);
assert.equal(get().plannerTabs[0].role, 'reference');
assert.equal(get().plannerTabs[0].replicationOverride, 1);
assert.equal(get().plannerReplication.seedMode, 'explicit');
assert.deepEqual(get().exportWorkflow().metadata.gui.planner, exported.metadata.gui.planner);
get().duplicatePlannerTab(id);
assert.notEqual(get().plannerTabs[1].id, id);
assert.equal(get().plannerTabs[1].role, 'configuration');
assert.equal(get().plannerTabs[1].replicationOverride, 1);
const legacy = JSON.parse(JSON.stringify(exported));
delete legacy.metadata.gui.planner.replication;
legacy.seed = 0;
get().loadWorkflow(legacy);
assert.equal(get().plannerReplication.replicates, 1);
assert.equal(get().plannerReplication.seedMode, 'fresh');
get().clearWorkflow();
assert.equal(get().plannerReplication.seedMode, 'generated');
assert.equal(storage.get('opencellcomms-workflow'), previousSnapshot);
console.log('PASS: Empty startup despite cached project, explicit import/export, large seeds, defaults and duplicate/reference rules.');

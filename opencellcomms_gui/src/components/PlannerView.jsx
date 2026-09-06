import { useState, useCallback } from 'react';
import { Plus, X, Eye, EyeOff, Copy, ListChecks } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import ParametersDashboard from './ParametersDashboard';
import './PlannerView.css';

/**
 * PlannerView - Multiple named parameter configurations (tabs).
 * Each tab stores only the parameter values edited in it (a sparse diff);
 * everything else follows the canvas base values.
 * Tabs, replicate counts and seed settings are exported with the workflow.
 */
const PlannerView = () => {
  const {
    plannerTabs,
    plannerReplication, updatePlannerReplication,
    setPlannerTabReplication,
    activePlannerTabId,
    addPlannerTab,
    duplicatePlannerTab,
    removePlannerTab,
    renamePlannerTab,
    togglePlannerTab,
    setActivePlannerTab,
    updatePlannerTabParam,
    removePlannerTabParam,
  } = useWorkflowStore();

  const [renamingTabId, setRenamingTabId] = useState(null);
  const [renameValue, setRenameValue] = useState('');

  const replicateCount = plannerReplication.seedMode === 'explicit' ? plannerReplication.seeds.length : plannerReplication.replicates;
  const activeTab = plannerTabs.find((t) => t.id === activePlannerTabId);

  const handleStartRename = useCallback((tab) => {
    setRenamingTabId(tab.id);
    setRenameValue(tab.name);
  }, []);

  const handleFinishRename = useCallback(
    (tabId) => {
      if (renameValue.trim()) {
        renamePlannerTab(tabId, renameValue.trim());
      }
      setRenamingTabId(null);
    },
    [renameValue, renamePlannerTab]
  );

  const handleUpdateParam = useCallback(
    (paramNodeId, updater) => {
      if (!activePlannerTabId) return;
      updatePlannerTabParam(activePlannerTabId, paramNodeId, updater);
    },
    [activePlannerTabId, updatePlannerTabParam]
  );

  const handleResetParam = useCallback(
    (paramNodeId) => {
      if (!activePlannerTabId) return;
      removePlannerTabParam(activePlannerTabId, paramNodeId);
    },
    [activePlannerTabId, removePlannerTabParam]
  );

  const handleClone = useCallback(
    (e, tabId) => {
      e.stopPropagation();
      duplicatePlannerTab(tabId);
    },
    [duplicatePlannerTab]
  );

  const handleDelete = useCallback(
    (e, tabId) => {
      e.stopPropagation();
      removePlannerTab(tabId);
    },
    [removePlannerTab]
  );

  const handleToggle = useCallback(
    (e, tabId) => {
      e.stopPropagation();
      togglePlannerTab(tabId);
    },
    [togglePlannerTab]
  );

  return (
    <div className="planner-view">
      {/* Tab bar */}
      <div className="planner-tab-bar">
        <button className="planner-add-btn" onClick={addPlannerTab} title="New configuration">
          <Plus size={14} />
          <span>New</span>
        </button>

        <div className="planner-tabs-scroll">
          {plannerTabs.map((tab) => (
            <div
              key={tab.id}
              className={`planner-tab ${tab.id === activePlannerTabId ? 'active' : ''} ${!tab.enabled ? 'disabled' : ''}`}
              onClick={() => setActivePlannerTab(tab.id)}
            >
              {/* Enabled/disabled toggle */}
              <button
                className="planner-tab-toggle"
                onClick={(e) => handleToggle(e, tab.id)}
                title={tab.enabled ? 'Disable this configuration' : 'Enable this configuration'}
              >
                {tab.enabled ? <Eye size={12} /> : <EyeOff size={12} />}
              </button>

              {/* Tab name (double-click to rename) */}
              {renamingTabId === tab.id ? (
                <input
                  className="planner-tab-rename-input"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onBlur={() => handleFinishRename(tab.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleFinishRename(tab.id);
                    if (e.key === 'Escape') setRenamingTabId(null);
                  }}
                  onClick={(e) => e.stopPropagation()}
                  autoFocus
                />
              ) : (
                <span
                  className="planner-tab-name"
                  onDoubleClick={() => handleStartRename(tab)}
                >
                  {tab.name} · n={tab.replicationOverride ?? replicateCount}
                </span>
              )}

              {/* Clone button */}
              <button
                className="planner-tab-clone"
                onClick={(e) => handleClone(e, tab.id)}
                title="Duplicate this configuration next to it"
              >
                <Copy size={12} />
              </button>

              {/* Delete button */}
              <button
                className="planner-tab-delete"
                onClick={(e) => handleDelete(e, tab.id)}
                title="Remove configuration"
              >
                <X size={12} />
              </button>
            </div>
          ))}
        </div>
      </div>

      <section className="planner-replication">
        <div className="planner-settings-row">
          <strong>Replication</strong>
          <label>Replicates per configuration
            <input aria-label="Replicates per configuration" type="number" min="1" max="10000"
              value={replicateCount} disabled={plannerReplication.seedMode === 'explicit'}
              onChange={(e) => updatePlannerReplication({ replicates: e.target.value })} />
          </label>
          <label>Seed assignment <select value={plannerReplication.seedMode}
            onChange={(e) => updatePlannerReplication({ seedMode: e.target.value, ...(e.target.value === 'explicit' ? { pairing: 'shared' } : {}) })}>
            <option value="generated">From saved master seed</option><option value="explicit">Explicit seed list</option>
            <option value="fresh">Fresh seeds for this launch</option>
          </select></label>
          {plannerReplication.seedMode === 'generated' && <label>Master seed
            <input aria-label="Master seed" type="text" inputMode="numeric" value={plannerReplication.masterSeed}
              onChange={(e) => updatePlannerReplication({ masterSeed: e.target.value })} /></label>}
          <label>Across configurations <select value={plannerReplication.pairing} disabled={plannerReplication.seedMode === 'explicit'}
            onChange={(e) => updatePlannerReplication({ pairing: e.target.value })}>
            <option value="shared">Shared seeds (paired comparisons)</option><option value="independent">Independent seed sets</option>
          </select></label>
        </div>
        {plannerReplication.seedMode === 'explicit' && <label>Positive integer seeds, separated by commas
          <input className="planner-explicit-seeds" aria-label="Explicit seeds" type="text"
            value={plannerReplication.seeds.join(',')}
            onChange={(e) => updatePlannerReplication({ seeds: e.target.value.split(',') })} />
        </label>}
        <div className="planner-settings-row">
          {activeTab && <label>Replicates for {activeTab.name}
            <input aria-label="Configuration replicate override" type="number" min="1" max="10000"
              placeholder="Use default" value={activeTab.replicationOverride ?? ''}
              onChange={(e) => setPlannerTabReplication(activeTab.id, e.target.value === '' ? null : e.target.value)} />
          </label>}
        </div>
      </section>
      {/* Content area */}
      <div className="planner-content">
        {plannerTabs.length === 0 ? (
          <div className="planner-empty">
            <ListChecks size={48} strokeWidth={1.5} />
            <h2>No Planner Configurations</h2>
            <p>
              Click <strong>+ New</strong> to create a parameter configuration.
              Each configuration stores only the values you change; everything else
              follows the canvas. Active configurations run sequentially when
              you press Run.
            </p>
          </div>
        ) : activeTab ? (
          <ParametersDashboard
            overrideData={activeTab.parameterOverrides}
            onUpdateParam={handleUpdateParam}
            onResetParam={handleResetParam}
          />
        ) : (
          <div className="planner-empty">
            <p>Select a tab to view its parameters.</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PlannerView;

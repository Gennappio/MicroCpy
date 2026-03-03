import { useState, useCallback } from 'react';
import { Plus, X, Eye, EyeOff, ListChecks } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import ParametersDashboard from './ParametersDashboard';
import './PlannerView.css';

/**
 * PlannerView - Multiple named parameter configurations (tabs).
 * Each tab holds its own copy of parameter values (overrides).
 * When "Run" is pressed in the console, all active tabs execute sequentially.
 */
const PlannerView = () => {
  const {
    plannerTabs,
    activePlannerTabId,
    addPlannerTab,
    removePlannerTab,
    renamePlannerTab,
    togglePlannerTab,
    setActivePlannerTab,
    updatePlannerTabParam,
  } = useWorkflowStore();

  const [renamingTabId, setRenamingTabId] = useState(null);
  const [renameValue, setRenameValue] = useState('');

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
                  {tab.name}
                </span>
              )}

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

      {/* Content area */}
      <div className="planner-content">
        {plannerTabs.length === 0 ? (
          <div className="planner-empty">
            <ListChecks size={48} strokeWidth={1.5} />
            <h2>No Planner Configurations</h2>
            <p>
              Click <strong>+ New</strong> to create a parameter configuration.
              Each configuration captures the current parameter values and lets you
              modify them independently. Active configurations run sequentially when
              you press Run.
            </p>
          </div>
        ) : activeTab ? (
          <ParametersDashboard
            overrideData={activeTab.parameterOverrides}
            onUpdateParam={handleUpdateParam}
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

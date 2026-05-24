import { useState } from 'react';
import { Plus, X, Users } from 'lucide-react';
import WorkflowCanvas from './WorkflowCanvas';
import FunctionPalette from './FunctionPalette';
import NodeInspector from './NodeInspector';
import BehaviorTabsBar from './BehaviorTabsBar';
import useWorkflowStore from '../store/workflowStore';
import './AgentsView.css';

const AgentsView = ({ paletteWidth, inspectorWidth, onMouseDownPalette, onMouseDownInspector }) => {
  const {
    workflow,
    currentStage,
    setCurrentStage,
    addAgentKind,
    removeAgentKind,
    addAgentBehavior,
    removeAgentBehavior,
    renameSubWorkflow,
    inspector,
  } = useWorkflowStore();

  const agentKinds = workflow.metadata?.gui?.agent_kinds || [];
  const [selectedKind, setSelectedKind] = useState(agentKinds[0]?.name || null);
  const [showAddKind, setShowAddKind] = useState(false);
  const [newKindName, setNewKindName] = useState('');
  const [showAddBehavior, setShowAddBehavior] = useState(false);
  const [newBehaviorName, setNewBehaviorName] = useState('');

  const activeKind = agentKinds.find((k) => k.name === selectedKind) || agentKinds[0] || null;

  const handleCreateKind = () => {
    const name = newKindName.trim();
    if (!name || !/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) return;
    addAgentKind(name);
    setSelectedKind(name);
    setNewKindName('');
    setShowAddKind(false);
  };

  const handleCreateBehavior = () => {
    if (!activeKind) return;
    const name = newBehaviorName.trim();
    if (!name || !/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) return;
    addAgentBehavior(activeKind.name, name);
    setCurrentStage(name);
    setNewBehaviorName('');
    setShowAddBehavior(false);
  };

  const handleDeleteBehavior = (behaviorName) => {
    if (!activeKind) return;
    if (!window.confirm(`Delete behavior "${behaviorName}"?`)) return;
    removeAgentBehavior(activeKind.name, behaviorName);
    if (currentStage === behaviorName) {
      setCurrentStage(activeKind.init_subworkflow);
    }
  };

  const buildTabs = (kind) => {
    if (!kind) return [];
    const tabs = [{ name: kind.init_subworkflow, label: 'Init', deletable: false }];
    (kind.behavior_subworkflows || []).forEach((b) => tabs.push({ name: b, label: b, deletable: true }));
    return tabs;
  };

  const inspectorOpen = inspector.isOpen;
  const gridStyle = inspectorOpen
    ? { gridTemplateColumns: `${paletteWidth}px 1fr ${inspectorWidth}px` }
    : { gridTemplateColumns: `${paletteWidth}px 1fr` };

  return (
    <div className="agents-view">
      {/* Left sidebar: agent kind selector */}
      <div className="agents-sidebar">
        <div className="agents-sidebar-header">
          <Users size={16} />
          <span>Agent Kinds</span>
        </div>
        {agentKinds.map((k) => (
          <div
            key={k.name}
            className={`agent-kind-chip ${selectedKind === k.name ? 'active' : ''}`}
            onClick={() => {
              setSelectedKind(k.name);
              setCurrentStage(k.init_subworkflow);
            }}
          >
            <span className="agent-kind-name">{k.name}</span>
            <span
              className="agent-kind-delete"
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm(`Delete agent kind "${k.name}" and all its behaviors?`)) {
                  removeAgentKind(k.name);
                  if (selectedKind === k.name) setSelectedKind(agentKinds[0]?.name || null);
                }
              }}
              title="Remove kind"
            >
              <X size={12} />
            </span>
          </div>
        ))}
        <button className="agent-kind-add" onClick={() => setShowAddKind(true)}>
          <Plus size={14} /> New Agent Kind
        </button>
      </div>

      {/* Main area */}
      <div className="agents-main">
        {activeKind ? (
          <>
            {/* Secondary tab bar: Init + behaviors */}
            <BehaviorTabsBar
              tabs={buildTabs(activeKind)}
              activeTab={currentStage}
              onTabClick={setCurrentStage}
              onAddTab={() => setShowAddBehavior(true)}
              onDeleteTab={handleDeleteBehavior}
              onRenameTab={(old, nw) => renameSubWorkflow(old, nw)}
              accentColor="#3b82f6"
              addLabel="New Behavior"
            />

            {/* Canvas + palette */}
            <div className={`workflow-grid ${inspectorOpen ? 'with-inspector' : ''}`} style={gridStyle}>
              <div className="grid-palette">
                <FunctionPalette currentStage={currentStage} />
                <div className="resize-handle resize-handle-right" onMouseDown={onMouseDownPalette} />
              </div>
              <div className="grid-canvas">
                <WorkflowCanvas key={currentStage} stage={currentStage} />
              </div>
              {inspectorOpen && (
                <div className="grid-inspector">
                  <div className="resize-handle resize-handle-left" onMouseDown={onMouseDownInspector} />
                  <NodeInspector />
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="agents-empty">
            <Users size={48} opacity={0.3} />
            <p>No agent kinds defined yet.</p>
            <button className="btn btn-primary" onClick={() => setShowAddKind(true)}>
              <Plus size={16} /> Add Agent Kind
            </button>
          </div>
        )}
      </div>

      {/* Add Kind Dialog */}
      {showAddKind && (
        <div className="dialog-overlay" onClick={() => setShowAddKind(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>New Agent Kind</h3>
            <p className="dialog-hint">Give the kind a name (e.g. <code>tumor_cell</code>, <code>immune_cell</code>).</p>
            <input
              className="dialog-input"
              placeholder="e.g. tumor_cell"
              value={newKindName}
              autoFocus
              onChange={(e) => setNewKindName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleCreateKind(); else if (e.key === 'Escape') setShowAddKind(false); }}
            />
            <div className="dialog-actions">
              <button className="btn btn-secondary" onClick={() => setShowAddKind(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleCreateKind}>Create</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Behavior Dialog */}
      {showAddBehavior && (
        <div className="dialog-overlay" onClick={() => setShowAddBehavior(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>New Behavior for <em>{activeKind?.name}</em></h3>
            <p className="dialog-hint">Give the behavior a name (e.g. <code>gene_network_update</code>).</p>
            <input
              className="dialog-input"
              placeholder="e.g. gene_network_update"
              value={newBehaviorName}
              autoFocus
              onChange={(e) => setNewBehaviorName(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleCreateBehavior(); else if (e.key === 'Escape') setShowAddBehavior(false); }}
            />
            <div className="dialog-actions">
              <button className="btn btn-secondary" onClick={() => setShowAddBehavior(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleCreateBehavior}>Create</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentsView;

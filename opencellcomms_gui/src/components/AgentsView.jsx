import { useState, useEffect } from 'react';
import { Plus, X, Users } from 'lucide-react';
import WorkflowCanvas from './WorkflowCanvas';
import FunctionPalette from './FunctionPalette';
import NodeInspector from './NodeInspector';
import BehaviorTabsBar from './BehaviorTabsBar';
import ExportBehaviorButton from './ExportBehaviorButton';
import useWorkflowStore from '../store/workflowStore';
import './AgentsView.css';

// The Agents-tab canvas to land on for a kind: its collective Creation canvas if it
// has one, else its per-agent init, else its first Step behavior, else null (a kind
// created collectively inside another kind's canvas, with no canvases of its own).
const landingStageFor = (kind) =>
  kind?.create_subworkflow || kind?.init_subworkflow || kind?.behavior_subworkflows?.[0] || null;

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
    // A new kind gets a collective Creation canvas — land on it.
    setCurrentStage(`${name}_create`);
    setNewKindName('');
    setShowAddKind(false);
  };

  // Keep currentStage in sync with the active kind: if the user lands on this
  // view (or the selected kind changes) and currentStage doesn't belong to
  // this kind, jump to its first canvas (Creation). Otherwise the FunctionPalette
  // sees currentStage='__scheduler__' and disables "New Function".
  useEffect(() => {
    if (!activeKind) return;
    const validNames = [activeKind.create_subworkflow, activeKind.init_subworkflow, ...(activeKind.behavior_subworkflows || [])].filter(Boolean);
    if (!validNames.includes(currentStage)) {
      setCurrentStage(landingStageFor(activeKind));
    }
  }, [activeKind?.name]);

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
      const remaining = (activeKind.behavior_subworkflows || []).filter((b) => b !== behaviorName);
      setCurrentStage(activeKind.create_subworkflow || activeKind.init_subworkflow || remaining[0] || null);
    }
  };

  const buildTabs = (kind) => {
    if (!kind) return [];
    const tabs = [];
    // Collective Creation canvas (runs once, env.agent is None) — first, if present.
    if (kind.create_subworkflow) {
      tabs.push({ name: kind.create_subworkflow, label: 'Creation', deletable: false });
    }
    // Per-agent Init canvas (for_each) — only kinds that have one (e.g. TCELL).
    if (kind.init_subworkflow) {
      tabs.push({ name: kind.init_subworkflow, label: 'Init', deletable: false });
    }
    (kind.behavior_subworkflows || []).forEach((b) => {
      tabs.push({ name: b, label: b, deletable: true });
    });
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
              setCurrentStage(landingStageFor(k));
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
            {/* Secondary tab bar: Init (only if the kind has a per-agent init) + behaviors */}
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

            {landingStageFor(activeKind) ? (
              /* Canvas + palette */
              <div className={`workflow-grid ${inspectorOpen ? 'with-inspector' : ''}`} style={gridStyle}>
                <div className="grid-palette">
                  <FunctionPalette currentStage={currentStage} />
                  <div className="resize-handle resize-handle-right" onMouseDown={onMouseDownPalette} />
                </div>
                <div className="grid-canvas">
                  <ExportBehaviorButton />
                  <WorkflowCanvas key={currentStage} stage={currentStage} />
                </div>
                {inspectorOpen && (
                  <div className="grid-inspector">
                    <div className="resize-handle resize-handle-left" onMouseDown={onMouseDownInspector} />
                    <NodeInspector />
                  </div>
                )}
              </div>
            ) : (
              /* A kind with no canvas of its own — created collectively inside another
                 kind's Creation (e.g. one CSV places several kinds). */
              <div className="agents-empty">
                <Users size={48} opacity={0.3} />
                <p>
                  Agents of kind <strong>{activeKind.name}</strong> have no canvas of their
                  own — they're created collectively (e.g. inside another kind's Creation)
                  and take no per-step behaviour.
                </p>
                <p>Add one with <strong>New Behavior</strong> if they should act each step.</p>
              </div>
            )}
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

import { useState, useEffect } from 'react';
import { Plus, X, Users } from 'lucide-react';
import WorkflowCanvas from './WorkflowCanvas';
import FunctionPalette from './FunctionPalette';
import NodeInspector from './NodeInspector';
import BehaviorTabsBar from './BehaviorTabsBar';
import ExportBehaviorButton from './ExportBehaviorButton';
import useWorkflowStore from '../store/workflowStore';
import { KIND_TO_TAB, KINDS } from '../store/subworkflowKinds';
import './AgentsView.css';

// The canvases the Agents tab shows for a kind, DERIVED from the single
// KIND_TO_TAB ownership map: its per-agent Steps, plus the collective Creation
// canvas only IF the map assigns agent_create to the Agents tab. It doesn't —
// creation is World-owned — so in practice this is Steps only. Because this and
// WorldView both read the same map, they can never disagree about where creation
// is authored (the mistake this guards against).
const buildTabs = (kind) => {
  if (!kind) return [];
  const tabs = [];
  if (kind.create_subworkflow && KIND_TO_TAB[KINDS.AGENT_CREATE] === 'agents') {
    tabs.push({ name: kind.create_subworkflow, label: 'Creation', deletable: false });
  }
  (kind.behavior_subworkflows || []).forEach((b) => tabs.push({ name: b, label: b, deletable: true }));
  return tabs;
};

// The Agents-tab canvas to land on for a kind: its first owned canvas, else null.
const landingStageFor = (kind) => buildTabs(kind)[0]?.name || null;

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
    // A new kind's collective Creation canvas is authored in the World tab; the
    // Agents tab shows only its per-agent Steps (none yet) — land on the empty state.
    setCurrentStage(null);
    setNewKindName('');
    setShowAddKind(false);
  };

  // Keep currentStage in sync with the active kind: if the user lands on this
  // view (or the selected kind changes) and currentStage doesn't belong to
  // this kind, jump to its first Step canvas. Otherwise the FunctionPalette
  // sees currentStage='__scheduler__' and disables "New Function".
  useEffect(() => {
    if (!activeKind) return;
    const validNames = buildTabs(activeKind).map((t) => t.name);
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
      const remaining = buildTabs(activeKind).map((t) => t.name).filter((n) => n !== behaviorName);
      setCurrentStage(remaining[0] || null);
    }
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
              /* Per-agent Steps only in this tab. This kind has none yet; its
                 collective Creation canvas is authored in the World tab. */
              <div className="agents-empty">
                <Users size={48} opacity={0.3} />
                <p>
                  Agents of kind <strong>{activeKind.name}</strong> have no per-step
                  behaviour yet. They're brought into existence in the <strong>World</strong>{' '}
                  tab (their collective Creation canvas); this tab holds their per-agent Steps.
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

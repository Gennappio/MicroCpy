import { useState, useEffect } from 'react';
import { Plus, X, Boxes } from 'lucide-react';
import WorkflowCanvas from './WorkflowCanvas';
import FunctionPalette from './FunctionPalette';
import NodeInspector from './NodeInspector';
import BehaviorTabsBar from './BehaviorTabsBar';
import ExportBehaviorButton from './ExportBehaviorButton';
import useWorkflowStore from '../store/workflowStore';
import './AgentsView.css';

/**
 * Resources tab — a full mirror of AgentsView for resource fields. Each resource
 * kind has a Setup canvas (seed the field) and Step canvases (growback/decay),
 * authored as nodes exactly like agent behaviours. Same canvas/palette/inspector.
 */
const ResourcesView = ({ paletteWidth, inspectorWidth, onMouseDownPalette, onMouseDownInspector }) => {
  const {
    workflow,
    currentStage,
    setCurrentStage,
    addResourceKind,
    removeResourceKind,
    addResourceBehavior,
    removeResourceBehavior,
    renameSubWorkflow,
    inspector,
  } = useWorkflowStore();

  const resourceKinds = workflow.metadata?.gui?.resource_kinds || [];
  const [selectedKind, setSelectedKind] = useState(resourceKinds[0]?.name || null);
  const [showAddKind, setShowAddKind] = useState(false);
  const [newKindName, setNewKindName] = useState('');
  const [showAddBehavior, setShowAddBehavior] = useState(false);
  const [newBehaviorName, setNewBehaviorName] = useState('');

  const activeKind = resourceKinds.find((k) => k.name === selectedKind) || resourceKinds[0] || null;

  const handleCreateKind = () => {
    const name = newKindName.trim();
    if (!name || !/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) return;
    addResourceKind(name);
    setSelectedKind(name);
    setCurrentStage(`${name}_init`);
    setNewKindName('');
    setShowAddKind(false);
  };

  useEffect(() => {
    if (!activeKind) return;
    const validNames = [activeKind.init_subworkflow, ...(activeKind.behavior_subworkflows || [])];
    if (!validNames.includes(currentStage)) {
      setCurrentStage(activeKind.init_subworkflow);
    }
  }, [activeKind?.name]);

  const handleCreateBehavior = () => {
    if (!activeKind) return;
    const name = newBehaviorName.trim();
    if (!name || !/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) return;
    addResourceBehavior(activeKind.name, name);
    setCurrentStage(name);
    setNewBehaviorName('');
    setShowAddBehavior(false);
  };

  const handleDeleteBehavior = (behaviorName) => {
    if (!activeKind) return;
    if (!window.confirm(`Delete step "${behaviorName}"?`)) return;
    removeResourceBehavior(activeKind.name, behaviorName);
    if (currentStage === behaviorName) {
      setCurrentStage(activeKind.init_subworkflow);
    }
  };

  const buildTabs = (kind) => {
    if (!kind) return [];
    const tabs = [
      { name: kind.init_subworkflow, label: 'Init', deletable: false },
    ];
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
      <div className="agents-sidebar">
        <div className="agents-sidebar-header">
          <Boxes size={16} />
          <span>Resources</span>
        </div>
        {resourceKinds.map((k) => (
          <div
            key={k.name}
            className={`agent-kind-chip ${selectedKind === k.name ? 'active' : ''}`}
            onClick={() => { setSelectedKind(k.name); setCurrentStage(k.init_subworkflow); }}
          >
            <span className="agent-kind-name">{k.name}</span>
            <span
              className="agent-kind-delete"
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm(`Delete resource "${k.name}" and all its steps?`)) {
                  removeResourceKind(k.name);
                  if (selectedKind === k.name) setSelectedKind(resourceKinds[0]?.name || null);
                }
              }}
              title="Remove resource"
            >
              <X size={12} />
            </span>
          </div>
        ))}
        <button className="agent-kind-add" onClick={() => setShowAddKind(true)}>
          <Plus size={14} /> New Resource
        </button>
      </div>

      <div className="agents-main">
        {activeKind ? (
          <>
            <BehaviorTabsBar
              tabs={buildTabs(activeKind)}
              activeTab={currentStage}
              onTabClick={setCurrentStage}
              onAddTab={() => setShowAddBehavior(true)}
              onDeleteTab={handleDeleteBehavior}
              onRenameTab={(old, nw) => renameSubWorkflow(old, nw)}
              accentColor="#10b981"
              addLabel="New Step"
            />
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
          </>
        ) : (
          <div className="agents-empty">
            <Boxes size={48} opacity={0.3} />
            <p>No resources defined yet.</p>
            <button className="btn btn-primary" onClick={() => setShowAddKind(true)}>
              <Plus size={16} /> Add Resource
            </button>
          </div>
        )}
      </div>

      {showAddKind && (
        <div className="dialog-overlay" onClick={() => setShowAddKind(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>New Resource</h3>
            <p className="dialog-hint">Give the field a name (e.g. <code>sugar</code>, <code>oxygen</code>).</p>
            <input
              className="dialog-input"
              placeholder="e.g. sugar"
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

      {showAddBehavior && (
        <div className="dialog-overlay" onClick={() => setShowAddBehavior(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>New Step for <em>{activeKind?.name}</em></h3>
            <p className="dialog-hint">Give the step a name (e.g. <code>growback</code>, <code>decay</code>).</p>
            <input
              className="dialog-input"
              placeholder="e.g. growback"
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

export default ResourcesView;

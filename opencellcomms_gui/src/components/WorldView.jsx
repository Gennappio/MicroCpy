import { useState, useEffect } from 'react';
import { Globe } from 'lucide-react';
import WorkflowCanvas from './WorkflowCanvas';
import FunctionPalette from './FunctionPalette';
import NodeInspector from './NodeInspector';
import BehaviorTabsBar from './BehaviorTabsBar';
import ExportBehaviorButton from './ExportBehaviorButton';
import useWorkflowStore from '../store/workflowStore';
import './AgentsView.css';

/**
 * World tab — the world setup canvas plus per-step collective behaviours.
 *
 * Setup (`world.subworkflow`) builds the grid + Domain + Population; drop
 * `setup_world` or a custom grid-builder. It is ordered first in the
 * Initialization tab. World behaviours (`world.behavior_subworkflows`) are
 * collective per-step subworkflows that run once each step inside the scheduler
 * (e.g. diffusion, world stepping) — they are NOT homed to an agent/resource
 * kind (which would force per-entity iteration) and are NOT processing (which
 * would run them post-loop).
 */
const WorldView = ({ paletteWidth, inspectorWidth, onMouseDownPalette, onMouseDownInspector }) => {
  const {
    workflow,
    currentStage,
    setCurrentStage,
    ensureWorld,
    addWorldBehavior,
    removeWorldBehavior,
    renameSubWorkflow,
    inspector,
  } = useWorkflowStore();

  const worldMeta = workflow.metadata?.gui?.world || {};
  const worldSub = worldMeta.subworkflow;
  const behaviors = worldMeta.behavior_subworkflows || [];

  const [showAddBehavior, setShowAddBehavior] = useState(false);
  const [newBehaviorName, setNewBehaviorName] = useState('');

  // Ensure a world setup subworkflow exists, then land on it.
  useEffect(() => {
    ensureWorld?.();
  }, [ensureWorld]);

  // Keep currentStage in sync with this tab's canvases (setup + behaviors);
  // otherwise the FunctionPalette sees '__scheduler__' and disables "New Function".
  useEffect(() => {
    const valid = [worldSub, ...behaviors].filter(Boolean);
    if (worldSub && !valid.includes(currentStage)) {
      setCurrentStage(worldSub);
    }
  }, [worldSub, behaviors.join(','), currentStage]);

  const handleCreateBehavior = () => {
    const name = newBehaviorName.trim();
    if (!name || !/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) return;
    addWorldBehavior(name);
    setCurrentStage(name);
    setNewBehaviorName('');
    setShowAddBehavior(false);
  };

  const handleDeleteBehavior = (behaviorName) => {
    if (!window.confirm(`Delete world behavior "${behaviorName}"?`)) return;
    removeWorldBehavior(behaviorName);
    if (currentStage === behaviorName && worldSub) {
      setCurrentStage(worldSub);
    }
  };

  const tabs = [
    ...(worldSub ? [{ name: worldSub, label: 'Setup', deletable: false }] : []),
    ...behaviors.map((b) => ({ name: b, label: b, deletable: true })),
  ];

  const inspectorOpen = inspector.isOpen;
  const gridStyle = inspectorOpen
    ? { gridTemplateColumns: `${paletteWidth}px 1fr ${inspectorWidth}px` }
    : { gridTemplateColumns: `${paletteWidth}px 1fr` };

  return (
    <div className="agents-view">
      <div className="agents-main">
        <div style={{ padding: '8px 14px', fontSize: '0.82rem', color: '#6b7280' }}>
          <Globe size={13} style={{ verticalAlign: '-2px', marginRight: 6 }} />
          <strong>World.</strong> Build the world grid in <em>Setup</em> (drop <code>setup_world</code>),
          and add per-step collective behaviours (e.g. diffusion) that run once each step.
        </div>

        <BehaviorTabsBar
          tabs={tabs}
          activeTab={currentStage}
          onTabClick={setCurrentStage}
          onAddTab={() => setShowAddBehavior(true)}
          onDeleteTab={handleDeleteBehavior}
          onRenameTab={(old, nw) => renameSubWorkflow(old, nw)}
          accentColor="#10b981"
          addLabel="New World Behavior"
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
      </div>

      {/* Add World Behavior Dialog */}
      {showAddBehavior && (
        <div className="dialog-overlay" onClick={() => setShowAddBehavior(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>New World Behavior</h3>
            <p className="dialog-hint">A collective per-step behaviour (e.g. <code>diffusion_step</code>).</p>
            <input
              className="dialog-input"
              placeholder="e.g. diffusion_step"
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

export default WorldView;

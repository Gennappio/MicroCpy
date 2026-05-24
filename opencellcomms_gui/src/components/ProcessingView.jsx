import { useState, useEffect } from 'react';
import { Sparkles } from 'lucide-react';
import WorkflowCanvas from './WorkflowCanvas';
import FunctionPalette from './FunctionPalette';
import NodeInspector from './NodeInspector';
import BehaviorTabsBar from './BehaviorTabsBar';
import useWorkflowStore from '../store/workflowStore';
import './ProcessingView.css';

const ProcessingView = ({ paletteWidth, inspectorWidth, onMouseDownPalette, onMouseDownInspector }) => {
  const {
    workflow,
    currentStage,
    setCurrentStage,
    addProcessingBehavior,
    removeProcessingBehavior,
    renameSubWorkflow,
    inspector,
  } = useWorkflowStore();

  const behaviors = workflow.metadata?.gui?.processing?.behavior_subworkflows || [];

  const [showAddBehavior, setShowAddBehavior] = useState(false);
  const [newBehaviorName, setNewBehaviorName] = useState('');

  // Sync currentStage on entry: jump to the first behavior if currentStage
  // doesn't belong to this view.
  useEffect(() => {
    if (behaviors.length > 0 && !behaviors.includes(currentStage)) {
      setCurrentStage(behaviors[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [behaviors.join(',')]);

  const handleCreateBehavior = () => {
    const name = newBehaviorName.trim();
    if (!name || !/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) return;
    addProcessingBehavior(name);
    setCurrentStage(name);
    setNewBehaviorName('');
    setShowAddBehavior(false);
  };

  const handleDeleteBehavior = (name) => {
    if (!window.confirm(`Delete processing behavior "${name}"?`)) return;
    removeProcessingBehavior(name);
    if (currentStage === name) {
      setCurrentStage(behaviors.find((b) => b !== name) || '__scheduler__');
    }
  };

  const tabs = behaviors.map((b) => ({ name: b, label: b, deletable: true }));
  const inspectorOpen = inspector.isOpen;
  const gridStyle = inspectorOpen
    ? { gridTemplateColumns: `${paletteWidth}px 1fr ${inspectorWidth}px` }
    : { gridTemplateColumns: `${paletteWidth}px 1fr` };

  return (
    <div className="processing-view">
      {behaviors.length > 0 ? (
        <>
          <BehaviorTabsBar
            tabs={tabs}
            activeTab={currentStage}
            onTabClick={setCurrentStage}
            onAddTab={() => setShowAddBehavior(true)}
            onDeleteTab={handleDeleteBehavior}
            onRenameTab={(old, nw) => renameSubWorkflow(old, nw)}
            accentColor="#8b5cf6"
            addLabel="New Processing Behavior"
          />
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
        <div className="processing-empty">
          <Sparkles size={48} opacity={0.3} />
          <p>No post-processing behaviors defined yet.</p>
          <button className="btn btn-primary" onClick={() => setShowAddBehavior(true)}>
            Add Processing Behavior
          </button>
        </div>
      )}

      {showAddBehavior && (
        <div className="dialog-overlay" onClick={() => setShowAddBehavior(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>New Processing Behavior</h3>
            <p className="dialog-hint">e.g. <code>generate_plots</code>, <code>export_csv</code></p>
            <input
              className="dialog-input"
              placeholder="e.g. generate_plots"
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

export default ProcessingView;

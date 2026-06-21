import { useState, useEffect } from 'react';
import { Globe } from 'lucide-react';
import WorkflowCanvas from './WorkflowCanvas';
import FunctionPalette from './FunctionPalette';
import NodeInspector from './NodeInspector';
import BehaviorTabsBar from './BehaviorTabsBar';
import ExportBehaviorButton from './ExportBehaviorButton';
import useWorkflowStore from '../store/workflowStore';
import './EnvironmentView.css';

const EnvironmentView = ({ paletteWidth, inspectorWidth, onMouseDownPalette, onMouseDownInspector }) => {
  const {
    workflow,
    currentStage,
    setCurrentStage,
    ensureEnvironmentInit,
    addEnvironmentBehavior,
    removeEnvironmentBehavior,
    renameSubWorkflow,
    inspector,
  } = useWorkflowStore();

  const envMeta = workflow.metadata?.gui?.environment || {};
  const initSw = envMeta.init_subworkflow;
  const behaviors = envMeta.behavior_subworkflows || [];

  const [showAddBehavior, setShowAddBehavior] = useState(false);
  const [newBehaviorName, setNewBehaviorName] = useState('');

  // Sync currentStage when entering this view: jump to init (or first behavior)
  // if currentStage isn't one of this view's tabs.
  useEffect(() => {
    const valid = [initSw, ...behaviors].filter(Boolean);
    if (valid.length > 0 && !valid.includes(currentStage)) {
      setCurrentStage(valid[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initSw, behaviors.join(',')]);

  const handleCreateBehavior = () => {
    const name = newBehaviorName.trim();
    if (!name || !/^[a-zA-Z][a-zA-Z0-9_]*$/.test(name)) return;
    addEnvironmentBehavior(name);
    setCurrentStage(name);
    setNewBehaviorName('');
    setShowAddBehavior(false);
  };

  const handleDeleteBehavior = (name) => {
    if (!window.confirm(`Delete environment behavior "${name}"?`)) return;
    removeEnvironmentBehavior(name);
    if (currentStage === name) {
      setCurrentStage(initSw || behaviors[0] || '__scheduler__');
    }
  };

  const handleEnsureInit = () => {
    ensureEnvironmentInit();
    const envM = workflow.metadata?.gui?.environment;
    if (envM?.init_subworkflow) setCurrentStage(envM.init_subworkflow);
    else setCurrentStage('environment_init');
  };

  const buildTabs = () => {
    const tabs = [];
    if (initSw) tabs.push({ name: initSw, label: 'Init', deletable: false });
    behaviors.forEach((b) => tabs.push({ name: b, label: b, deletable: true }));
    return tabs;
  };

  const hasContent = initSw || behaviors.length > 0;
  const inspectorOpen = inspector.isOpen;
  const gridStyle = inspectorOpen
    ? { gridTemplateColumns: `${paletteWidth}px 1fr ${inspectorWidth}px` }
    : { gridTemplateColumns: `${paletteWidth}px 1fr` };

  return (
    <div className="environment-view">
      {hasContent ? (
        <>
          <BehaviorTabsBar
            tabs={buildTabs()}
            activeTab={currentStage}
            onTabClick={setCurrentStage}
            onAddTab={() => setShowAddBehavior(true)}
            onDeleteTab={handleDeleteBehavior}
            onRenameTab={(old, nw) => renameSubWorkflow(old, nw)}
            accentColor="#10b981"
            addLabel="New Behavior"
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
        <div className="environment-empty">
          <Globe size={48} opacity={0.3} />
          <p>No environment defined yet.</p>
          <div className="environment-empty-actions">
            <button className="btn btn-primary" onClick={handleEnsureInit}>
              Add Init Canvas
            </button>
            <button className="btn btn-secondary" onClick={() => setShowAddBehavior(true)}>
              Add Behavior
            </button>
          </div>
        </div>
      )}

      {showAddBehavior && (
        <div className="dialog-overlay" onClick={() => setShowAddBehavior(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h3>New Environment Behavior</h3>
            <p className="dialog-hint">e.g. <code>diffusion_step</code>, <code>nutrient_update</code></p>
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

export default EnvironmentView;

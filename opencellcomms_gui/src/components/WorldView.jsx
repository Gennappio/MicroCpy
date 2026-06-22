import { useEffect } from 'react';
import { Globe } from 'lucide-react';
import WorkflowCanvas from './WorkflowCanvas';
import FunctionPalette from './FunctionPalette';
import NodeInspector from './NodeInspector';
import ExportBehaviorButton from './ExportBehaviorButton';
import useWorkflowStore from '../store/workflowStore';
import { WORLD_NAME } from '../store/subworkflowKinds';
import './AgentsView.css';

/**
 * World tab — its own canvas, just like Agents and Resources.
 *
 * The palette offers the standard `setup_world` node (builds the grid + Domain +
 * Population); drop it and edit its parameters, or create a custom grid-builder
 * with "New Function". One world per model. It is one init behaviour, ordered in
 * the Initialization tab alongside the entity Setups. (Domain/Population are built
 * by setup_world and have no tabs of their own.)
 */
const WorldView = ({ paletteWidth, inspectorWidth, onMouseDownPalette, onMouseDownInspector }) => {
  const { ensureWorld, setCurrentStage, inspector } = useWorkflowStore();

  useEffect(() => {
    ensureWorld?.();
    setCurrentStage(WORLD_NAME);
  }, [ensureWorld, setCurrentStage]);

  const inspectorOpen = inspector.isOpen;
  const gridStyle = inspectorOpen
    ? { gridTemplateColumns: `${paletteWidth}px 1fr ${inspectorWidth}px` }
    : { gridTemplateColumns: `${paletteWidth}px 1fr` };

  return (
    <div className="agents-view">
      <div className="agents-main">
        <div style={{ padding: '8px 14px', fontSize: '0.82rem', color: '#6b7280' }}>
          <Globe size={13} style={{ verticalAlign: '-2px', marginRight: 6 }} />
          <strong>World.</strong> Build the world grid: drop <code>setup_world</code> (size, topology),
          or create a custom grid-builder. Order it first in the Initialization tab.
        </div>
        <div className={`workflow-grid ${inspectorOpen ? 'with-inspector' : ''}`} style={gridStyle}>
          <div className="grid-palette">
            <FunctionPalette currentStage={WORLD_NAME} />
            <div className="resize-handle resize-handle-right" onMouseDown={onMouseDownPalette} />
          </div>
          <div className="grid-canvas">
            <ExportBehaviorButton />
            <WorkflowCanvas key={WORLD_NAME} stage={WORLD_NAME} />
          </div>
          {inspectorOpen && (
            <div className="grid-inspector">
              <div className="resize-handle resize-handle-left" onMouseDown={onMouseDownInspector} />
              <NodeInspector />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorldView;

import { useEffect } from 'react';
import { Globe } from 'lucide-react';
import WorkflowCanvas from './WorkflowCanvas';
import FunctionPalette from './FunctionPalette';
import NodeInspector from './NodeInspector';
import ExportBehaviorButton from './ExportBehaviorButton';
import useWorkflowStore from '../store/workflowStore';
import { SPACE_NAME } from '../store/subworkflowKinds';
import './AgentsView.css';

/**
 * Space tab — its own canvas, just like Agents and Resources.
 *
 * The palette offers the standard `setup_space` node (builds the grid + Domain +
 * Population); drop it and edit its parameters, or create a custom grid-builder
 * with "New Function". One space per model. It is one init behaviour, ordered in
 * the Initialization tab alongside the entity Setups. (Domain/Population are built
 * by setup_space and have no tabs of their own.)
 */
const SpaceView = ({ paletteWidth, inspectorWidth, onMouseDownPalette, onMouseDownInspector }) => {
  const { ensureSpace, setCurrentStage, inspector } = useWorkflowStore();

  useEffect(() => {
    ensureSpace?.();
    setCurrentStage(SPACE_NAME);
  }, [ensureSpace, setCurrentStage]);

  const inspectorOpen = inspector.isOpen;
  const gridStyle = inspectorOpen
    ? { gridTemplateColumns: `${paletteWidth}px 1fr ${inspectorWidth}px` }
    : { gridTemplateColumns: `${paletteWidth}px 1fr` };

  return (
    <div className="agents-view">
      <div className="agents-main">
        <div style={{ padding: '8px 14px', fontSize: '0.82rem', color: '#6b7280' }}>
          <Globe size={13} style={{ verticalAlign: '-2px', marginRight: 6 }} />
          <strong>Space.</strong> Build the world grid: drop <code>setup_space</code> (size, topology),
          or create a custom grid-builder. Order it first in the Initialization tab.
        </div>
        <div className={`workflow-grid ${inspectorOpen ? 'with-inspector' : ''}`} style={gridStyle}>
          <div className="grid-palette">
            <FunctionPalette currentStage={SPACE_NAME} />
            <div className="resize-handle resize-handle-right" onMouseDown={onMouseDownPalette} />
          </div>
          <div className="grid-canvas">
            <ExportBehaviorButton />
            <WorkflowCanvas key={SPACE_NAME} stage={SPACE_NAME} />
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

export default SpaceView;

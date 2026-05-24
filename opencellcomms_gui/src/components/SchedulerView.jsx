import WorkflowCanvas from './WorkflowCanvas';
import NodeInspector from './NodeInspector';
import SchedulerPalette from './SchedulerPalette';
import useWorkflowStore from '../store/workflowStore';
import { SCHEDULER_NAME } from '../store/subworkflowKinds';
import './SchedulerView.css';

const SchedulerView = ({ paletteWidth, inspectorWidth, onMouseDownPalette, onMouseDownInspector }) => {
  const { inspector } = useWorkflowStore();
  const inspectorOpen = inspector.isOpen;

  const gridStyle = inspectorOpen
    ? { gridTemplateColumns: `${paletteWidth}px 1fr ${inspectorWidth}px` }
    : { gridTemplateColumns: `${paletteWidth}px 1fr` };

  return (
    <div className="scheduler-view">
      <div className="scheduler-header">
        <span className="scheduler-hint">
          Drag behaviors from the palette onto the canvas to schedule them into the main loop. Order matters.
        </span>
      </div>
      <div className={`workflow-grid ${inspectorOpen ? 'with-inspector' : ''}`} style={gridStyle}>
        <div className="grid-palette">
          <SchedulerPalette />
          <div className="resize-handle resize-handle-right" onMouseDown={onMouseDownPalette} />
        </div>
        <div className="grid-canvas">
          <WorkflowCanvas key={SCHEDULER_NAME} stage={SCHEDULER_NAME} />
        </div>
        {inspectorOpen && (
          <div className="grid-inspector">
            <div className="resize-handle resize-handle-left" onMouseDown={onMouseDownInspector} />
            <NodeInspector />
          </div>
        )}
      </div>
    </div>
  );
};

export default SchedulerView;

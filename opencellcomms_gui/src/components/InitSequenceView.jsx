import { useEffect, useMemo } from 'react';
import { AlertTriangle } from 'lucide-react';
import WorkflowCanvas from './WorkflowCanvas';
import NodeInspector from './NodeInspector';
import InitSequencePalette from './InitSequencePalette';
import useWorkflowStore from '../store/workflowStore';
import { INIT_SEQUENCE_NAME } from '../store/subworkflowKinds';
import './InitSequenceView.css';

const InitSequenceView = ({ paletteWidth, inspectorWidth, onMouseDownPalette, onMouseDownInspector }) => {
  const { workflow, inspector, ensureInitSequence, setCurrentStage } = useWorkflowStore();
  const inspectorOpen = inspector.isOpen;

  useEffect(() => {
    ensureInitSequence();
    setCurrentStage(INIT_SEQUENCE_NAME);
  }, [ensureInitSequence, setCurrentStage]);

  // Warn when the user has defined init subworkflows that aren't yet scheduled.
  const unscheduledInits = useMemo(() => {
    const calls = workflow.subworkflows?.[INIT_SEQUENCE_NAME]?.subworkflow_calls || [];
    const scheduled = new Set(calls.map((c) => c.subworkflow_name));

    const defined = [];
    const envInit = workflow.metadata?.gui?.environment?.init_subworkflow;
    if (envInit) defined.push(envInit);
    (workflow.metadata?.gui?.agent_kinds || []).forEach((k) => {
      if (k.init_subworkflow) defined.push(k.init_subworkflow);
    });
    return defined.filter((name) => !scheduled.has(name));
  }, [workflow]);

  const gridStyle = inspectorOpen
    ? { gridTemplateColumns: `${paletteWidth}px 1fr ${inspectorWidth}px` }
    : { gridTemplateColumns: `${paletteWidth}px 1fr` };

  return (
    <div className="init-sequence-view">
      <div className="init-sequence-header">
        <span className="init-sequence-hint">
          Drag init subworkflows from the palette onto the canvas to set initialization order.
          Runs once at the start of the simulation.
        </span>
      </div>
      {unscheduledInits.length > 0 && (
        <div className="init-sequence-warning">
          <AlertTriangle size={14} />
          <span>
            <strong>Init subworkflows defined but not scheduled:</strong>{' '}
            {unscheduledInits.join(', ')}. Drag them onto the canvas — or your simulation will skip them.
          </span>
        </div>
      )}
      <div className={`workflow-grid ${inspectorOpen ? 'with-inspector' : ''}`} style={gridStyle}>
        <div className="grid-palette">
          <InitSequencePalette />
          <div className="resize-handle resize-handle-right" onMouseDown={onMouseDownPalette} />
        </div>
        <div className="grid-canvas">
          <WorkflowCanvas key={INIT_SEQUENCE_NAME} stage={INIT_SEQUENCE_NAME} />
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

export default InitSequenceView;

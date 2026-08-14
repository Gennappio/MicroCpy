import { Handle, Position } from 'reactflow';
import { Zap, Settings } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import './InitNode.css';

/**
 * Init / controller node — the starting point of execution flow.
 * Can't be deleted, always present on every canvas. Pure visual; toolbar
 * actions (like Export Behavior) live in ExportBehaviorButton, not here.
 */
const InitNode = ({ id, data, selected }) => {
  const label = data?.label || 'INIT';

  // Every controller exposes a "Number of steps" parameter handle: wiring a
  // steps parameter node to it makes that node the loop count for this
  // subworkflow (the executor resolves it directly). The Scheduler's node is
  // auto-created; on other canvases the count defaults to 1 (run once) until
  // a node is wired.
  const numberOfSteps = data?.numberOfSteps || 1;
  const isParameterConnected = data?.isStepsParameterConnected || false;
  const connectedParameterValue = data?.connectedStepsValue;

  // An enabled Planner configuration can override the steps parameter at run
  // time; flag it so the displayed count isn't mistaken for what will run.
  const plannerTabs = useWorkflowStore((s) => s.plannerTabs);
  const plannerShadowed =
    isParameterConnected &&
    !!data?.stepsParamNodeId &&
    plannerTabs.some((t) => t.enabled && t.parameterOverrides?.[data.stepsParamNodeId]);

  return (
    <div className={`init-node ${selected ? 'selected' : ''}`}>
      <div className="init-settings-icon">
        <Settings size={16} />
      </div>

      <div className="init-node-content">
        <Zap size={24} className="init-icon" />
        <span className="init-label">{label}</span>
      </div>

      <div className="init-parameter-section">
        <div className={`init-parameter-row ${isParameterConnected ? 'connected' : ''}`}>
          <Handle
            type="target"
            position={Position.Left}
            id="steps-param"
            className="init-parameter-handle"
            style={{
              background: '#3b82f6',
              width: '10px',
              height: '10px',
              border: '2px solid white',
              left: '-5px',
            }}
          />
          <span className="init-parameter-label">
            Number of steps: {isParameterConnected && connectedParameterValue !== undefined ? connectedParameterValue : numberOfSteps}
          </span>
          {plannerShadowed && (
            <span
              className="init-planner-badge"
              title="One or more enabled Planner configurations override this value; planner runs use the tab value."
            >
              Planner
            </span>
          )}
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        id="init-out"
        className="init-handle-output"
        style={{
          background: '#dc2626',
          width: '12px',
          height: '12px',
          border: '3px solid white',
        }}
      />
    </div>
  );
};

export default InitNode;

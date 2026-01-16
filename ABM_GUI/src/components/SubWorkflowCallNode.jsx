import { Handle, Position, useEdges, useNodes } from 'reactflow';
import { Settings, Play, Pause, Zap, ExternalLink } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import NodeBadge from './NodeBadge';
import './SubWorkflowCallNode.css';

/**
 * Custom node component for sub-workflow calls
 * Purple color for sub-workflows, orange/gold for composers
 */
const SubWorkflowCallNode = ({ id, data, selected }) => {
  const toggleFunctionEnabled = useWorkflowStore((state) => state.toggleFunctionEnabled);
  const setCurrentStage = useWorkflowStore((state) => state.setCurrentStage);
  const workflow = useWorkflowStore((state) => state.workflow);
  const currentStage = useWorkflowStore((state) => state.currentStage);
  const nodeBadgeStatsByScope = useWorkflowStore((state) => state.nodeBadgeStatsByScope);
  const openInspector = useWorkflowStore((state) => state.openInspector);
  const edges = useEdges();
  const nodes = useNodes();

  const { label, subworkflowName, iterations, enabled, onEdit, description } = data;

  // Get badge stats for this node
  const subworkflowKind = workflow.metadata?.gui?.subworkflow_kinds?.[currentStage] || 'subworkflow';
  const scopeKey = `${subworkflowKind}:${currentStage}`;
  const badgeStats = nodeBadgeStatsByScope[scopeKey]?.[id] || null;

  // Handle badge click - open inspector to appropriate tab
  const handleBadgeClick = (badgeType) => {
    const tabMap = {
      status: 'overview',
      timing: 'overview',
      logs: 'logs',
      context: 'context',
    };
    openInspector(tabMap[badgeType] || 'overview');
  };

  // Determine if this is calling a composer
  const targetKind = workflow.metadata?.gui?.subworkflow_kinds?.[subworkflowName] ||
                    (subworkflowName === 'main' ? 'composer' : 'subworkflow');
  const isComposerCall = targetKind === 'composer';

  const handleToggleEnabled = (e) => {
    e.stopPropagation();
    toggleFunctionEnabled(id);
  };

  return (
    <div
      className={`subworkflow-call-node ${isComposerCall ? 'composer-call' : ''} ${!enabled ? 'disabled' : ''} ${selected ? 'selected' : ''}`}
      style={{ width: '350px', padding: '8px', fontSize: '13px' }}
    >
      {/* Function flow handles (top and bottom) */}
      <Handle type="target" position={Position.Top} id="func-in" className="function-handle" />

      <div className="node-header">
        <button
          className="node-status"
          onClick={handleToggleEnabled}
          title={enabled ? 'Disable node' : 'Enable node'}
        >
          {enabled ? (
            <Play size={14} className="status-icon enabled" />
          ) : (
            <Pause size={14} className="status-icon disabled" />
          )}
        </button>
        <div className="node-icon">
          <Zap size={16} className="subworkflow-icon" />
        </div>
        <div className="node-title">
          {label || subworkflowName}
        </div>
        {onEdit && (
          <button
            className="node-edit-btn"
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            title="Edit parameters"
          >
            <Settings size={14} />
          </button>
        )}
        <button
          className="node-goto-btn"
          onClick={(e) => {
            e.stopPropagation();
            setCurrentStage(subworkflowName);
          }}
          title={`Go to ${subworkflowName}`}
        >
          <ExternalLink size={14} />
        </button>
      </div>

      {/* Parameter handles section */}
      <div className="node-parameters">
        {(edges || [])
          .filter(edge => edge.target === id && edge.targetHandle?.startsWith('params-'))
          .map((edge) => {
            const handleId = edge.targetHandle;
            const paramNode = (nodes || []).find(n => n.id === edge.source);
            const paramLabel = paramNode?.data?.label || 'Parameters';
            const paramNames = paramNode?.data?.parameters
              ? Object.keys(paramNode.data.parameters).join(', ')
              : '';

            return (
              <div key={`param-handle-${handleId}`} className="parameter-row connected">
                <Handle
                  type="target"
                  position={Position.Left}
                  id={handleId}
                  className="parameter-handle-input"
                  style={{
                    top: 'auto',
                    background: '#8b5cf6',
                    backgroundColor: '#8b5cf6',
                    width: '8px',
                    height: '8px',
                    border: '2px solid white',
                    left: '-16px'
                  }}
                  title={`From: ${paramLabel}`}
                />
                <span className="parameter-label" title={paramNames}>
                  {paramLabel.replace(' Parameters', '').substring(0, 20)}
                  {paramLabel.length > 20 ? '...' : ''}
                </span>
              </div>
            );
          })}
      </div>

      <div className="node-subworkflow-name">
        Sub-workflow: {subworkflowName}
      </div>

      {iterations && iterations > 1 && (
        <div className="node-iterations" title="Number of times this sub-workflow executes">
          Iterations: {iterations}
        </div>
      )}

      {description && (
        <div className="node-description" title={description}>
          {description.substring(0, 50)}{description.length > 50 ? '...' : ''}
        </div>
      )}

      {/* Node observability badge (status, timing, log counts) */}
      <NodeBadge stats={badgeStats} onClick={handleBadgeClick} />

      {/* Function flow output handle on BOTTOM */}
      <Handle type="source" position={Position.Bottom} id="func-out" className="function-handle" />
    </div>
  );
};

export default SubWorkflowCallNode;


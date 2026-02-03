import { Handle, Position, useEdges } from 'reactflow';
import { Settings, Play, Pause, FileCode, MessageSquare } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import NodeBadge from './NodeBadge';
import { getFunction } from '../data/functionRegistry';
import './WorkflowFunctionNode.css';

/**
 * Custom node component for workflow functions
 *
 * IMPORTANT: Each function parameter is displayed as a socket on the LEFT side of the node.
 * Parameters are defined in the function registry and each has:
 * - name: displayed as label next to socket
 * - default: shown after the parameter name
 * - type: determines input validation
 */
const WorkflowFunctionNode = ({ id, data, selected }) => {
  const toggleFunctionEnabled = useWorkflowStore((state) => state.toggleFunctionEnabled);
  const toggleNodeVerbose = useWorkflowStore((state) => state.toggleNodeVerbose);
  const currentStage = useWorkflowStore((state) => state.currentStage);
  const workflow = useWorkflowStore((state) => state.workflow);
  const nodeBadgeStatsByScope = useWorkflowStore((state) => state.nodeBadgeStatsByScope);
  const openInspector = useWorkflowStore((state) => state.openInspector);

  const edges = useEdges(); // Use reactflow's useEdges hook

  const { label, functionName, enabled, onEdit, functionFile, parameters, customName, stepCount, verbose } = data;

  // Get function metadata from registry to get parameter definitions
  const funcMeta = getFunction(functionName);
  const parameterDefs = funcMeta?.parameters || [];

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

  // Get function file from data or parameters
  const filePath = functionFile || parameters?.function_file || '';
  const fileName = filePath ? filePath.split('/').pop() : '';

  // Determine display name and whether to show template indicator
  const isTemplate = !customName;
  const displayName = customName || label;

  // Check which parameters are connected via edges
  const connectedParams = new Set(
    (edges || [])
      .filter(edge => edge.target === id && edge.targetHandle?.startsWith('param-'))
      .map(edge => edge.targetHandle.replace('param-', ''))
  );

  const handleToggleEnabled = (e) => {
    e.stopPropagation();
    toggleFunctionEnabled(id);
  };

  const handleToggleVerbose = (e) => {
    e.stopPropagation();
    toggleNodeVerbose(id);
  };

  // Format default value for display
  const formatDefault = (value) => {
    if (value === undefined || value === null) return '';
    if (typeof value === 'boolean') return value ? 'true' : 'false';
    if (typeof value === 'string') {
      // Truncate long strings
      return value.length > 15 ? `"${value.substring(0, 12)}..."` : `"${value}"`;
    }
    if (typeof value === 'object') {
      return JSON.stringify(value).substring(0, 15) + '...';
    }
    return String(value);
  };

  // Get type indicator for parameter
  const getTypeIndicator = (paramType) => {
    if (!paramType) return null;
    const lowerType = paramType.toLowerCase();
    if (lowerType.includes('list') || lowerType.includes('array')) {
      return <span className="type-indicator type-list">[list]</span>;
    }
    if (lowerType.includes('dict') || lowerType.includes('object') || lowerType.includes('map')) {
      return <span className="type-indicator type-dict">[dict]</span>;
    }
    return null;
  };

  return (
    <div
      className={`workflow-function-node ${!enabled ? 'disabled' : ''} ${selected ? 'selected' : ''}`}
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
        <button
          className={`node-verbose ${verbose ? 'active' : ''}`}
          onClick={handleToggleVerbose}
          title={verbose ? 'Disable logging' : 'Enable logging'}
        >
          <MessageSquare size={14} className={verbose ? 'verbose-icon active' : 'verbose-icon'} />
        </button>
        <div className="node-title">
          {displayName}
          {isTemplate && <span className="template-badge">(template)</span>}
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
      </div>

      {/* Description hidden - only visible in settings dialog */}

      {/* Parameter handles section - LEFT SIDE sockets for each parameter */}
      {/* Each parameter from the function registry gets its own socket with label and default value */}
      {parameterDefs.length > 0 && (
        <div className="node-parameters">
          {parameterDefs.map((param) => {
            const isConnected = connectedParams.has(param.name);
            // Get current value from node's parameters, or use default
            const currentValue = parameters?.[param.name] ?? param.default;

            return (
              <div
                key={`param-${param.name}`}
                className={`parameter-row ${isConnected ? 'connected' : 'disconnected'}`}
              >
                <Handle
                  type="target"
                  position={Position.Left}
                  id={`param-${param.name}`}
                  className="parameter-handle-input"
                  style={{
                    top: 'auto',
                    background: isConnected ? '#10b981' : '#3b82f6',
                    backgroundColor: isConnected ? '#10b981' : '#3b82f6',
                    width: '8px',
                    height: '8px',
                    border: '2px solid white',
                    left: '-16px'
                  }}
                  title={`${param.name}: ${param.description || ''}`}
                />
                <span
                  className="parameter-label"
                  title={`${param.name}: ${param.description || ''}\nDefault: ${param.default}`}
                >
                  {param.name}
                  {param.required && <span className="required-indicator">*</span>}
                  {getTypeIndicator(param.type)}
                </span>
                {/* Only show value when NOT connected */}
                {!isConnected && (
                  <span className="parameter-value">
                    {formatDefault(currentValue)}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="node-function-name">{functionName}</div>

      {fileName && (
        <div className="node-file-path" title={filePath}>
          <FileCode size={12} />
          <span>{fileName}</span>
        </div>
      )}

      {stepCount && stepCount > 1 && (
        <div className="node-step-count" title="Number of times this function executes">
          Steps: {stepCount}
        </div>
      )}

      {/* Node observability badge (status, timing, log counts) */}
      <NodeBadge stats={badgeStats} onClick={handleBadgeClick} />

      {/* Function flow output handle on BOTTOM only - no right-side handles */}
      <Handle type="source" position={Position.Bottom} id="func-out" className="function-handle" />
    </div>
  );
};

export default WorkflowFunctionNode;


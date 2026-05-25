import { Handle, Position } from 'reactflow';
import { Zap, Settings, Upload } from 'lucide-react';
import { useState } from 'react';
import useWorkflowStore from '../store/workflowStore';
import { FUNCTION_HOSTING_KINDS } from '../store/subworkflowKinds';
import { fetchRegistry } from '../data/functionRegistry';
import './InitNode.css';

const InitNode = ({ id, data, selected }) => {
  const label = data?.label || 'INIT';
  const { workflow, currentStage, markUserFunctionExported, stageNodes } = useWorkflowStore();
  const [exporting, setExporting] = useState(false);

  // Allow Export Behavior on every canvas that can hold function nodes
  // (agent init/behavior, env init/behavior, processing behavior).
  const currentKind = workflow.metadata?.gui?.subworkflow_kinds?.[currentStage];
  const canExport = FUNCTION_HOSTING_KINDS.has(currentKind);

  // Check if this is the macrostep controller (needs "Number of steps" parameter)
  const isMacrostepController = id.includes('macrostep');

  // Get the number of steps value (default to 1)
  const numberOfSteps = data?.numberOfSteps || 1;

  // Check if the parameter is connected to a parameter node
  const isParameterConnected = data?.isStepsParameterConnected || false;

  // Get the connected parameter value (if connected)
  const connectedParameterValue = data?.connectedStepsValue;

  const handleExportBehavior = async () => {
    setExporting(true);
    try {
      const userFns = workflow.metadata?.gui?.user_functions || [];

      // 1. Gather function nodes on this canvas
      const canvasNodes = (stageNodes[currentStage] || []).filter((n) => n.type === 'workflowFunction');
      const canvasFnNames = new Set(canvasNodes.map((n) => n.data?.functionName).filter(Boolean));

      // 2. Find user_functions that need exporting:
      //    - present on this canvas AND not yet exported
      //    - OR staged for this behavior even if not on canvas (per plan 12B)
      const toExport = userFns.filter((f) =>
        f.exported === false && (canvasFnNames.has(f.name) || f.behavior === currentStage)
      );

      if (toExport.length === 0) {
        alert('Nothing to export — no unsaved functions on this canvas for behavior "' + currentStage + '".');
        return;
      }

      // 3. Group by file_path
      const byFile = new Map();
      for (const f of toExport) {
        if (!f.file_path) {
          alert(`Function "${f.name}" has no file_path — re-create it via "New Function".`);
          return;
        }
        if (!byFile.has(f.file_path)) byFile.set(f.file_path, []);
        byFile.get(f.file_path).push({ name: f.name, parameters: f.parameters || [] });
      }

      // 4. POST scaffold per group
      const results = [];
      for (const [filePath, fns] of byFile.entries()) {
        const res = await fetch('http://localhost:5001/api/function/scaffold', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ file_path: filePath, functions: fns }),
        });
        const data = await res.json();
        results.push({ filePath, data });
        if (!data.success) {
          alert(`Failed to export to ${filePath}: ${data.error}`);
          return;
        }
      }

      // 5. Mark all exported
      for (const f of toExport) markUserFunctionExported(f.name);

      // 6. Refresh registry so new functions become draggable with full metadata
      await fetchRegistry();

      const summary = results.map((r) =>
        `${r.filePath}\n  added: ${r.data.added_functions?.join(', ') || 'none'}` +
        (r.data.skipped_existing?.length ? `\n  skipped (existing): ${r.data.skipped_existing.join(', ')}` : '') +
        (r.data.reload_warning ? `\n  ⚠ ${r.data.reload_warning}` : '')
      ).join('\n\n');
      alert(`Exported behavior "${currentStage}":\n\n${summary}`);
    } catch (e) {
      alert('Export failed: ' + e.message);
    } finally {
      setExporting(false);
    }
  };

  // Check if there's anything pending for this canvas (drives button highlight)
  const userFns = workflow.metadata?.gui?.user_functions || [];
  const canvasNodes = stageNodes?.[currentStage] || [];
  const canvasFnNames = new Set(canvasNodes.filter(n => n.type === 'workflowFunction').map(n => n.data?.functionName).filter(Boolean));
  const pendingCount = userFns.filter(f =>
    f.exported === false && (canvasFnNames.has(f.name) || f.behavior === currentStage)
  ).length;

  return (
    <div className={`init-node ${selected ? 'selected' : ''}`}>
      <div className="init-settings-icon">
        <Settings size={16} />
      </div>

      <div className="init-node-content">
        <Zap size={24} className="init-icon" />
        <span className="init-label">{label}</span>
      </div>

      {/* Export Behavior button — visible on canvases that host functions */}
      {canExport && (
        <button
          className={`init-generate-btn ${pendingCount > 0 ? 'has-pending' : ''}`}
          onClick={handleExportBehavior}
          disabled={exporting}
          title={pendingCount > 0
            ? `Write ${pendingCount} pending function(s) to disk`
            : 'No unsaved functions to export'}
        >
          <Upload size={13} />
          {exporting ? 'Exporting…' : `Export Behavior${pendingCount > 0 ? ` (${pendingCount})` : ''}`}
        </button>
      )}

      {/* Number of steps parameter (only for macrostep controller) */}
      {isMacrostepController && (
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
          </div>
        </div>
      )}

      {/* Output handle - connects to first function in execution chain */}
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


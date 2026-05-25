import { useState } from 'react';
import { Upload } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import { FUNCTION_HOSTING_KINDS } from '../store/subworkflowKinds';
import { fetchRegistry } from '../data/functionRegistry';
import './ExportBehaviorButton.css';

/**
 * Floating top-right button over the canvas. Only renders on canvases that
 * can host function nodes (not on scheduler / not on read-only views).
 *
 * Gathers unsaved user_functions for the current stage, groups by file path,
 * POSTs /api/function/scaffold per group, marks them exported, and refreshes
 * the registry.
 */
const ExportBehaviorButton = () => {
  const {
    workflow,
    currentStage,
    stageNodes,
    markUserFunctionExported,
  } = useWorkflowStore();
  const [exporting, setExporting] = useState(false);

  const currentKind = workflow.metadata?.gui?.subworkflow_kinds?.[currentStage];
  const canExport = FUNCTION_HOSTING_KINDS.has(currentKind);

  // Compute pending count (cheap — runs on every render but the lists are tiny)
  const userFns = workflow.metadata?.gui?.user_functions || [];
  const nodes = stageNodes?.[currentStage] || [];
  const canvasFnNames = new Set(
    nodes
      .filter((n) => n.type === 'workflowFunction')
      .map((n) => n.data?.functionName)
      .filter(Boolean)
  );
  const pending = userFns.filter(
    (f) => f.exported === false && (canvasFnNames.has(f.name) || f.behavior === currentStage)
  );

  if (!canExport) return null;

  const handleExport = async () => {
    setExporting(true);
    try {
      if (pending.length === 0) {
        alert(`Nothing to export — no unsaved functions for behavior "${currentStage}".`);
        return;
      }

      // Group by file path
      const byFile = new Map();
      for (const f of pending) {
        if (!f.file_path) {
          alert(`Function "${f.name}" has no file_path — re-create it via "New Function".`);
          return;
        }
        if (!byFile.has(f.file_path)) byFile.set(f.file_path, []);
        byFile.get(f.file_path).push({ name: f.name, parameters: f.parameters || [] });
      }

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

      for (const f of pending) markUserFunctionExported(f.name);
      await fetchRegistry();

      const summary = results
        .map(
          (r) =>
            `${r.filePath}\n  added: ${r.data.added_functions?.join(', ') || 'none'}` +
            (r.data.skipped_existing?.length
              ? `\n  skipped (existing): ${r.data.skipped_existing.join(', ')}`
              : '') +
            (r.data.reload_warning ? `\n  ⚠ ${r.data.reload_warning}` : '')
        )
        .join('\n\n');
      alert(`Exported behavior "${currentStage}":\n\n${summary}`);
    } catch (e) {
      alert('Export failed: ' + e.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <button
      className={`export-behavior-btn ${pending.length > 0 ? 'has-pending' : ''}`}
      onClick={handleExport}
      disabled={exporting}
      title={
        pending.length > 0
          ? `Write ${pending.length} pending function(s) to disk`
          : 'No unsaved functions to export'
      }
    >
      <Upload size={14} />
      {exporting ? 'Exporting…' : `Export Behavior${pending.length > 0 ? ` (${pending.length})` : ''}`}
    </button>
  );
};

export default ExportBehaviorButton;

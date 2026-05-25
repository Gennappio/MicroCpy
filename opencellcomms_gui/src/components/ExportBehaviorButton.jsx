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
/**
 * Derive the .subworkflow.json sibling path from a function's file_path.
 * e.g. "opencellcomms_adapters/X/functions/intracellular/foo.py" + "foo"
 *      → "opencellcomms_adapters/X/functions/intracellular/foo.subworkflow.json"
 */
const derivePairedJsonPath = (anchorPyPath, behaviorName) => {
  if (!anchorPyPath) return null;
  // Pop the filename, keep the directory
  const lastSep = Math.max(anchorPyPath.lastIndexOf('/'), anchorPyPath.lastIndexOf('\\'));
  const dir = lastSep >= 0 ? anchorPyPath.slice(0, lastSep) : '.';
  return `${dir}/${behaviorName}.subworkflow.json`;
};

const ExportBehaviorButton = () => {
  const {
    workflow,
    currentStage,
    stageNodes,
    markUserFunctionExported,
    exportSingleSubworkflow,
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
      // Determine an anchor path for the paired .subworkflow.json. Prefer the
      // first staged user_function's directory; otherwise prompt the user.
      let anchorPath = null;
      if (pending.length > 0 && pending[0].file_path) {
        anchorPath = pending[0].file_path;
      } else {
        const allUserFns = workflow.metadata?.gui?.user_functions || [];
        const anyForBehavior = allUserFns.find((f) => f.behavior === currentStage && f.file_path);
        if (anyForBehavior) anchorPath = anyForBehavior.file_path;
      }

      // ── Step 1: scaffold .py files for any pending functions ──────────
      const pyResults = [];
      if (pending.length > 0) {
        const byFile = new Map();
        for (const f of pending) {
          if (!f.file_path) {
            alert(`Function "${f.name}" has no file_path — re-create it via "New Function".`);
            return;
          }
          if (!byFile.has(f.file_path)) byFile.set(f.file_path, []);
          byFile.get(f.file_path).push({ name: f.name, parameters: f.parameters || [] });
        }

        for (const [filePath, fns] of byFile.entries()) {
          const res = await fetch('http://localhost:5001/api/function/scaffold', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ file_path: filePath, functions: fns }),
          });
          const data = await res.json();
          pyResults.push({ filePath, data });
          if (!data.success) {
            alert(`Failed to export to ${filePath}: ${data.error}`);
            return;
          }
        }
        for (const f of pending) markUserFunctionExported(f.name);
      }

      // ── Step 2: pick the .subworkflow.json target path ────────────────
      // If we still have no anchor (behavior built entirely from existing
      // registry functions), ask the user via the native save dialog.
      let jsonTargetPath;
      if (anchorPath) {
        jsonTargetPath = derivePairedJsonPath(anchorPath, currentStage);
      } else {
        const dialogRes = await fetch('http://localhost:5001/api/filesystem/save-dialog', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            default_path: `opencellcomms_engine/exports/${currentStage}.subworkflow.json`,
          }),
        });
        const dialogData = await dialogRes.json();
        if (dialogData.cancelled || !dialogData.path) {
          if (pyResults.length > 0) {
            alert('Wrote .py file(s) but skipped .subworkflow.json (no target selected).');
          } else {
            alert('Export cancelled.');
          }
          await fetchRegistry();
          return;
        }
        jsonTargetPath = dialogData.path;
      }

      // ── Step 3: build and write the paired .subworkflow.json ──────────
      const exportData = exportSingleSubworkflow(currentStage);
      if (!exportData) {
        alert('Failed to build subworkflow JSON for ' + currentStage);
        return;
      }
      const jsonContent = JSON.stringify(exportData, null, 2);

      const writeRes = await fetch('http://localhost:5001/api/filesystem/write-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ file_path: jsonTargetPath, content: jsonContent }),
      });
      const writeData = await writeRes.json();
      if (!writeData.success) {
        alert(`Wrote .py file(s) but failed to write .subworkflow.json: ${writeData.error}`);
        return;
      }

      // ── Step 4: refresh registry and summarise ────────────────────────
      await fetchRegistry();

      const pySummary = pyResults
        .map(
          (r) =>
            `  ${r.filePath}\n    added: ${r.data.added_functions?.join(', ') || 'none'}` +
            (r.data.skipped_existing?.length
              ? `\n    skipped: ${r.data.skipped_existing.join(', ')}`
              : '')
        )
        .join('\n');
      const jsonLine = `  ${writeData.file_path}` + (writeData.backup_path ? ' (existing backed up)' : ' (new)');
      const noPy = pyResults.length === 0 ? '\n(no new .py files written — all functions were already exported)\n' : '\n';
      alert(
        `Exported behavior "${currentStage}":\n` +
          (pySummary ? `\nPython files:\n${pySummary}` : noPy) +
          `\nStructure file:\n${jsonLine}`
      );
    } catch (e) {
      alert('Export failed: ' + e.message);
    } finally {
      setExporting(false);
    }
  };

  // Disable only when there's truly nothing in the behavior at all
  const canvasNodeCount = (stageNodes?.[currentStage] || []).filter(
    (n) => n.type === 'workflowFunction'
  ).length;
  const hasAnything = canvasNodeCount > 0 || pending.length > 0;

  return (
    <button
      className={`export-behavior-btn ${pending.length > 0 ? 'has-pending' : ''}`}
      onClick={handleExport}
      disabled={exporting || !hasAnything}
      title={
        !hasAnything
          ? 'Add function nodes first'
          : pending.length > 0
          ? `Write ${pending.length} pending .py file(s) + the structure .subworkflow.json`
          : 'Write the structure .subworkflow.json (no .py changes)'
      }
    >
      <Upload size={14} />
      {exporting ? 'Exporting…' : `Export Behavior${pending.length > 0 ? ` (${pending.length})` : ''}`}
    </button>
  );
};

export default ExportBehaviorButton;

import { useState, useMemo } from 'react';
import { X, Check, AlertTriangle, Zap, Box } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import './SubworkflowImportDialog.css';

/**
 * Dialog for selecting which subworkflows to import from a workflow file
 */
const SubworkflowImportDialog = ({
  workflowData,
  onImport,
  onCancel
}) => {
  const workflow = useWorkflowStore((state) => state.workflow);
  const getSubworkflowsFromWorkflowData = useWorkflowStore((state) => state.getSubworkflowsFromWorkflowData);

  // Get available subworkflows from the source file
  const availableSubworkflows = useMemo(() => {
    return getSubworkflowsFromWorkflowData(workflowData);
  }, [workflowData, getSubworkflowsFromWorkflowData]);

  // Track selected subworkflows and rename mappings
  const [selected, setSelected] = useState({});
  const [renameMap, setRenameMap] = useState({});

  // Check for conflicts with existing subworkflows
  const existingNames = useMemo(() => {
    return new Set(Object.keys(workflow.subworkflows || {}));
  }, [workflow.subworkflows]);

  const getConflictStatus = (name) => {
    const targetName = renameMap[name] || name;
    if (existingNames.has(targetName)) {
      return 'conflict';
    }
    return 'ok';
  };

  const toggleSelection = (name) => {
    setSelected(prev => ({
      ...prev,
      [name]: !prev[name]
    }));
  };

  const handleRename = (originalName, newName) => {
    setRenameMap(prev => ({
      ...prev,
      [originalName]: newName
    }));
  };

  const handleImport = () => {
    const selectedNames = Object.entries(selected)
      .filter(([, isSelected]) => isSelected)
      .map(([name]) => name);

    if (selectedNames.length === 0) {
      alert('Please select at least one subworkflow to import');
      return;
    }

    // Check for unresolved conflicts
    const unresolvedConflicts = selectedNames.filter(name => getConflictStatus(name) === 'conflict');
    if (unresolvedConflicts.length > 0) {
      alert(`Please resolve naming conflicts for: ${unresolvedConflicts.join(', ')}`);
      return;
    }

    onImport(selectedNames, renameMap);
  };

  const selectedCount = Object.values(selected).filter(Boolean).length;

  return (
    <div className="dialog-overlay" onClick={onCancel}>
      <div className="subworkflow-import-dialog" onClick={e => e.stopPropagation()}>
        <div className="dialog-header">
          <h3>Import from: {workflowData.name}</h3>
          <button className="close-btn" onClick={onCancel}>
            <X size={20} />
          </button>
        </div>

        <p className="dialog-description">
          Select subworkflows and composers to import into your project.
          Rename any that conflict with existing names.
        </p>

        <div className="subworkflow-list">
          {availableSubworkflows.map((sw) => {
            const isSelected = selected[sw.name] || false;
            const conflictStatus = getConflictStatus(sw.name);
            const targetName = renameMap[sw.name] || sw.name;
            const isComposer = sw.kind === 'composer';

            return (
              <div
                key={sw.name}
                className={`subworkflow-item ${isSelected ? 'selected' : ''} ${conflictStatus === 'conflict' ? 'has-conflict' : ''}`}
              >
                <div className="item-checkbox">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelection(sw.name)}
                    id={`sw-${sw.name}`}
                  />
                </div>

                <div className="item-content">
                  <div className="item-header">
                    <span className={`kind-badge ${isComposer ? 'composer' : 'subworkflow'}`}>
                      {isComposer ? <Box size={12} /> : <Zap size={12} />}
                      {isComposer ? 'Composer' : 'Subworkflow'}
                    </span>
                    <span className="item-name">{sw.name}</span>
                    {conflictStatus === 'conflict' && (
                      <span className="conflict-badge">
                        <AlertTriangle size={14} />
                        Name exists
                      </span>
                    )}
                  </div>

                  <div className="item-description">
                    {sw.description || 'No description'}
                  </div>

                  <div className="item-stats">
                    <span>{sw.functionCount} functions</span>
                    <span>{sw.callCount} calls</span>
                    {sw.dependencies.length > 0 && (
                      <span className="dependencies">
                        Needs: {sw.dependencies.join(', ')}
                      </span>
                    )}
                  </div>

                  {isSelected && (existingNames.has(sw.name) || renameMap[sw.name]) && (
                    <div className="rename-section">
                      <label>Import as:</label>
                      <input
                        type="text"
                        value={targetName}
                        onChange={(e) => handleRename(sw.name, e.target.value)}
                        placeholder="Enter new name"
                        className={conflictStatus === 'conflict' ? 'has-error' : ''}
                      />
                      {conflictStatus === 'ok' && renameMap[sw.name] && (
                        <Check size={16} className="ok-icon" />
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="dialog-actions">
          <span className="selection-count">
            {selectedCount} selected
          </span>
          <button className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleImport}
            disabled={selectedCount === 0}
          >
            Import Selected
          </button>
        </div>
      </div>
    </div>
  );
};

export default SubworkflowImportDialog;


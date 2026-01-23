import { useState, useMemo } from 'react';
import { X, Check, AlertTriangle, Zap, Box, Link } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import './SubworkflowImportDialog.css';

/**
 * Dialog for selecting which subworkflows to import from a workflow file
 * Automatically shows transitive dependencies that will be included
 */
const SubworkflowImportDialog = ({
  workflowData,
  onImport,
  onCancel
}) => {
  const workflow = useWorkflowStore((state) => state.workflow);
  const getSubworkflowsFromWorkflowData = useWorkflowStore((state) => state.getSubworkflowsFromWorkflowData);
  const collectAllDependencies = useWorkflowStore((state) => state.collectAllDependencies);

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

  // Compute all dependencies for the currently selected items
  const dependencyInfo = useMemo(() => {
    const selectedNames = Object.entries(selected)
      .filter(([, isSelected]) => isSelected)
      .map(([name]) => name);

    if (selectedNames.length === 0) {
      return {
        allSubworkflows: new Set(),
        directSelections: new Set(),
        autoDependencies: new Set(),
        missingDependencies: new Set()
      };
    }

    const info = collectAllDependencies(workflowData, selectedNames);
    const autoDeps = new Set();
    for (const name of info.allSubworkflows) {
      if (!info.directSelections.has(name)) {
        autoDeps.add(name);
      }
    }

    return {
      ...info,
      autoDependencies: autoDeps
    };
  }, [selected, workflowData, collectAllDependencies]);

  const getConflictStatus = (name) => {
    const targetName = renameMap[name] || name;
    // Check if target name already exists in current project
    if (existingNames.has(targetName)) {
      return 'conflict';
    }
    return 'ok';
  };

  const getItemStatus = (name) => {
    // Is this directly selected?
    if (selected[name]) {
      return 'selected';
    }
    // Is this an auto-dependency?
    if (dependencyInfo.autoDependencies.has(name)) {
      return 'auto-dependency';
    }
    return 'none';
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

    // Check for unresolved conflicts on directly selected items
    const unresolvedConflicts = selectedNames.filter(name => getConflictStatus(name) === 'conflict');
    if (unresolvedConflicts.length > 0) {
      alert(`Please resolve naming conflicts for: ${unresolvedConflicts.join(', ')}`);
      return;
    }

    // Also check auto-dependencies for conflicts (those that don't already exist)
    const autoDepsWithConflicts = [...dependencyInfo.autoDependencies]
      .filter(name => !existingNames.has(name)) // Skip those already in project (will be skipped on import)
      .filter(name => getConflictStatus(name) === 'conflict');

    if (autoDepsWithConflicts.length > 0) {
      alert(`Auto-dependency naming conflicts: ${autoDepsWithConflicts.join(', ')}\nThese need to be renamed.`);
      return;
    }

    onImport(selectedNames, renameMap);
  };

  const selectedCount = Object.values(selected).filter(Boolean).length;
  const autoDepsCount = dependencyInfo.autoDependencies.size;
  const totalImportCount = selectedCount + [...dependencyInfo.autoDependencies].filter(name => !existingNames.has(name)).length;

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
          Select subworkflows and composers to import. Dependencies are automatically included.
          {autoDepsCount > 0 && (
            <span className="auto-deps-note">
              <Link size={12} /> {autoDepsCount} dependencies will be auto-imported
            </span>
          )}
        </p>

        <div className="subworkflow-list">
          {availableSubworkflows.map((sw) => {
            const itemStatus = getItemStatus(sw.name);
            const isSelected = itemStatus === 'selected';
            const isAutoDep = itemStatus === 'auto-dependency';
            const conflictStatus = getConflictStatus(sw.name);
            const targetName = renameMap[sw.name] || sw.name;
            const isComposer = sw.kind === 'composer';
            const alreadyExists = existingNames.has(sw.name);

            // Determine the visual state
            const isIncluded = isSelected || isAutoDep;
            const willBeSkipped = isAutoDep && alreadyExists;

            return (
              <div
                key={sw.name}
                className={`subworkflow-item
                  ${isSelected ? 'selected' : ''}
                  ${isAutoDep ? 'auto-dependency' : ''}
                  ${willBeSkipped ? 'will-skip' : ''}
                  ${conflictStatus === 'conflict' && isIncluded && !willBeSkipped ? 'has-conflict' : ''}`}
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

                    {/* Status badges */}
                    {isAutoDep && !willBeSkipped && (
                      <span className="auto-dep-badge">
                        <Link size={12} />
                        Auto-included
                      </span>
                    )}
                    {willBeSkipped && (
                      <span className="skip-badge">
                        Already exists
                      </span>
                    )}
                    {conflictStatus === 'conflict' && isIncluded && !willBeSkipped && (
                      <span className="conflict-badge">
                        <AlertTriangle size={14} />
                        Name conflict
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

                  {/* Rename section for selected items with conflicts */}
                  {isIncluded && !willBeSkipped && (existingNames.has(sw.name) || renameMap[sw.name]) && (
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
            {autoDepsCount > 0 && (
              <span className="auto-deps-count"> + {autoDepsCount} deps</span>
            )}
            {totalImportCount > 0 && (
              <span className="total-count"> = {totalImportCount} total</span>
            )}
          </span>
          <button className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleImport}
            disabled={selectedCount === 0}
          >
            Import {totalImportCount > 0 ? `(${totalImportCount})` : ''}
          </button>
        </div>
      </div>
    </div>
  );
};

export default SubworkflowImportDialog;


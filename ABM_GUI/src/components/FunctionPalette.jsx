import { useState, useEffect, useRef } from 'react';
import { ChevronDown, ChevronRight, Database, Zap, Upload } from 'lucide-react';
import { getFunctionsByCategoryAsync, FunctionCategory, fetchRegistry } from '../data/functionRegistry';
import useWorkflowStore from '../store/workflowStore';
import LibraryConflictDialog from './LibraryConflictDialog';
import './FunctionPalette.css';

/**
 * Function Palette - Sidebar with draggable functions
 */
const FunctionPalette = ({ currentStage }) => {
  const workflow = useWorkflowStore((state) => state.workflow);
  const addFunctionLibrary = useWorkflowStore((state) => state.addFunctionLibrary);
  const [functionsByCategory, setFunctionsByCategory] = useState({});
  const [libraryFunctions, setLibraryFunctions] = useState({});  // Functions from imported libraries
  const [isLoading, setIsLoading] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState({
    [FunctionCategory.INITIALIZATION]: true,
    [FunctionCategory.INTRACELLULAR]: true,
    [FunctionCategory.MICROENVIRONMENT]: true,
    [FunctionCategory.INTERCELLULAR]: true,
    [FunctionCategory.FINALIZATION]: true,
    'subworkflows': true,
    'composers': true,
    'libraries': true,
  });
  const [conflictDialog, setConflictDialog] = useState(null);
  const fileInputRef = useRef(null);

  // Determine if current stage is a composer
  const currentKind = workflow.metadata?.gui?.subworkflow_kinds?.[currentStage] ||
                     (currentStage === 'main' ? 'composer' : 'subworkflow');
  const isComposer = currentKind === 'composer';

  // Load registry on mount and when stage changes
  useEffect(() => {
    const loadFunctions = async () => {
      setIsLoading(true);
      try {
        console.log('[PALETTE] Loading functions for stage:', currentStage);
        const registry = await fetchRegistry();
        console.log('[PALETTE] Registry loaded, total functions:', Object.keys(registry).length);

        // For v2.0 workflows, show all functions grouped by category
        // For v1.0 workflows, show only functions for the current stage
        if (workflow.version === '2.0') {
          // Group all functions by their category
          const grouped = {};
          Object.values(registry).forEach((func) => {
            const category = func.category;
            if (!grouped[category]) {
              grouped[category] = [];
            }
            grouped[category].push(func);
          });
          console.log('[PALETTE] v2.0 mode - showing all functions grouped by category');
          setFunctionsByCategory(grouped);
        } else {
          // v1.0 mode - show only functions for current stage
          const functions = await getFunctionsByCategoryAsync(currentStage);
          console.log('[PALETTE] v1.0 mode - functions for stage', currentStage, ':', functions.length);
          setFunctionsByCategory({ [currentStage]: functions });
        }
      } catch (error) {
        console.error('[PALETTE] Error loading functions:', error);
        setFunctionsByCategory({});
      } finally {
        setIsLoading(false);
      }
    };

    loadFunctions();
  }, [currentStage, workflow.version]);

  const toggleCategory = (category) => {
    setExpandedCategories((prev) => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  const onDragStart = (event, functionData) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify(functionData));
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDragStartParameter = (event) => {
    const parameterNodeData = {
      type: 'parameterNode',
      label: 'New Parameters',
      parameters: {},
    };
    event.dataTransfer.setData('application/reactflow', JSON.stringify(parameterNodeData));
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDragStartSubWorkflow = (event, subworkflowName) => {
    const subworkflowCallData = {
      type: 'subworkflowCall',
      subworkflowName: subworkflowName,
      label: subworkflowName,
      iterations: 1,
      parameters: {},
    };
    event.dataTransfer.setData('application/reactflow', JSON.stringify(subworkflowCallData));
    event.dataTransfer.effectAllowed = 'move';
  };

  const categoryLabels = {
    [FunctionCategory.INITIALIZATION]: 'Initialization',
    [FunctionCategory.INTRACELLULAR]: 'Intracellular',
    [FunctionCategory.MICROENVIRONMENT]: 'Microenvironment',
    [FunctionCategory.DIFFUSION]: 'Microenvironment',
    [FunctionCategory.INTERCELLULAR]: 'Intercellular',
    [FunctionCategory.FINALIZATION]: 'Finalization',
    [FunctionCategory.UTILITY]: 'Utility',
  };

  // Determine which categories to display
  const categoriesToDisplay = workflow.version === '2.0'
    ? [
        FunctionCategory.INITIALIZATION,
        FunctionCategory.INTRACELLULAR,
        FunctionCategory.DIFFUSION,
        FunctionCategory.INTERCELLULAR,
        FunctionCategory.FINALIZATION,
        FunctionCategory.UTILITY,
      ]
    : [currentStage];

  // Handle library import
  const handleImportLibrary = async () => {
    fileInputRef.current?.click();
  };

  const handleFileSelected = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Phase 6: Get absolute path for library
    // In Electron: file.path is available
    // In browser: prompt user for absolute path
    let libraryPath = file.path;
    if (!libraryPath) {
      libraryPath = prompt(
        `Enter the absolute path to the library file:\n\n` +
        `File name: ${file.name}\n\n` +
        `Example: /Users/yourname/projects/libs/${file.name}\n` +
        `or C:\\Users\\yourname\\projects\\libs\\${file.name}`,
        ''
      );

      if (!libraryPath) {
        alert('Library path is required for proper path handling.');
        return;
      }
    }

    try {
      // Parse the library file
      const response = await fetch('http://localhost:5001/api/library/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ library_path: libraryPath })
      });

      const data = await response.json();

      if (!data.success) {
        alert(`Error parsing library: ${data.error}`);
        return;
      }

      // Check for conflicts with existing functions
      const allExistingFunctions = new Set();
      Object.values(functionsByCategory).forEach(funcs => {
        funcs.forEach(f => allExistingFunctions.add(f.name));
      });
      Object.values(libraryFunctions).forEach(funcs => {
        funcs.forEach(f => allExistingFunctions.add(f.name));
      });

      const conflicts = data.functions.filter(f => allExistingFunctions.has(f.name));

      if (conflicts.length > 0) {
        // Show conflict resolution dialog
        setConflictDialog({
          conflicts: conflicts.map(f => ({
            functionName: f.name,
            existingSource: 'Built-in'  // TODO: track actual source
          })),
          libraryName: data.library_name,
          libraryPath: libraryPath,
          allFunctions: data.functions
        });
      } else {
        // No conflicts, add all functions
        const functionMappings = {};
        data.functions.forEach(f => {
          functionMappings[f.name] = 'add';
        });
        addFunctionLibrary(libraryPath, functionMappings);

        // Add to library functions display
        setLibraryFunctions(prev => ({
          ...prev,
          [data.library_name]: data.functions
        }));
      }
    } catch (error) {
      console.error('Error importing library:', error);
      alert(`Error importing library: ${error.message}`);
    }

    // Reset file input
    event.target.value = '';
  };

  const handleConflictResolution = (resolutions) => {
    const { libraryPath, libraryName, allFunctions } = conflictDialog;

    // Build function mappings based on resolutions
    const functionMappings = {};
    allFunctions.forEach(func => {
      const resolution = resolutions[func.name] || 'add';
      if (resolution !== 'skip') {
        functionMappings[func.name] = resolution;
      }
    });

    // Add library to workflow
    addFunctionLibrary(libraryPath, functionMappings);

    // Update library functions display
    const functionsToAdd = allFunctions.filter(f => {
      const resolution = resolutions[f.name] || 'add';
      return resolution !== 'skip';
    }).map(f => ({
      ...f,
      variant: resolutions[f.name] === 'variant' ? libraryName : null,
      function_file: resolutions[f.name] === 'variant' ? libraryPath : null
    }));

    setLibraryFunctions(prev => ({
      ...prev,
      [libraryName]: functionsToAdd
    }));

    setConflictDialog(null);
  };

  return (
    <div className="function-palette">
      <div className="palette-header">
        <h3>Function Library</h3>
        {workflow.version === '2.0' && !isComposer && (
          <button
            className="import-library-btn"
            onClick={handleImportLibrary}
            title="Import Function Library"
          >
            <Upload size={16} />
          </button>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept=".py"
          style={{ display: 'none' }}
          onChange={handleFileSelected}
        />
      </div>

      <div className="palette-content">
        {/* Parameter Node Section */}
        <div className="parameter-node-section">
          <div className="parameter-node-header">
            <Database size={16} />
            <span>Parameter Nodes</span>
          </div>
          <div
            className="parameter-node-draggable"
            draggable
            onDragStart={onDragStartParameter}
          >
            <Database size={14} />
            <div className="parameter-node-info">
              <div className="parameter-node-name">Parameters</div>
              <div className="parameter-node-desc">Drag to add parameter storage</div>
            </div>
          </div>
        </div>

        {/* Composers Section (v2.0 only) */}
        {workflow.version === '2.0' && (() => {
          const currentKind = workflow.metadata?.gui?.subworkflow_kinds?.[currentStage] ||
                             (currentStage === 'main' ? 'composer' : 'subworkflow');

          const availableComposers = Object.keys(workflow.subworkflows || {}).filter(name => {
            if (name === currentStage) return false;
            const targetKind = workflow.metadata?.gui?.subworkflow_kinds?.[name] ||
                              (name === 'main' ? 'composer' : 'subworkflow');
            // Only show composers
            if (targetKind !== 'composer') return false;
            // Sub-workflows cannot call composers
            if (currentKind === 'subworkflow') return false;
            return true;
          });

          if (availableComposers.length === 0) return null;

          return (
            <div className="palette-category">
              <div
                className="category-header"
                onClick={() => toggleCategory('composers')}
              >
                {expandedCategories['composers'] ? (
                  <ChevronDown size={16} />
                ) : (
                  <ChevronRight size={16} />
                )}
                <span>Composers</span>
                <span className="category-count">
                  {availableComposers.length}
                </span>
              </div>

              {expandedCategories['composers'] && (
                <div className="category-functions">
                  {availableComposers.map((composerName) => (
                    <div
                      key={composerName}
                      className="function-item subworkflow-item composer-item"
                      draggable
                      onDragStart={(e) => onDragStartSubWorkflow(e, composerName)}
                    >
                      <div className="function-item-icon">
                        <Zap size={14} />
                      </div>
                      <div className="function-item-name">{composerName}</div>
                      <div className="function-item-description">
                        {workflow.subworkflows[composerName].description || 'Composer call'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })()}

        {/* Sub-workflows Section (v2.0 only) */}
        {workflow.version === '2.0' && (() => {
          const currentKind = workflow.metadata?.gui?.subworkflow_kinds?.[currentStage] ||
                             (currentStage === 'main' ? 'composer' : 'subworkflow');

          const availableSubworkflows = Object.keys(workflow.subworkflows || {}).filter(name => {
            if (name === currentStage) return false;
            const targetKind = workflow.metadata?.gui?.subworkflow_kinds?.[name] ||
                              (name === 'main' ? 'composer' : 'subworkflow');
            // Only show sub-workflows (not composers)
            if (targetKind !== 'subworkflow') return false;
            return true;
          });

          if (availableSubworkflows.length === 0) return null;

          return (
            <div className="palette-category">
              <div
                className="category-header"
                onClick={() => toggleCategory('subworkflows')}
              >
                {expandedCategories['subworkflows'] ? (
                  <ChevronDown size={16} />
                ) : (
                  <ChevronRight size={16} />
                )}
                <span>Sub-workflows</span>
                <span className="category-count">
                  {availableSubworkflows.length}
                </span>
              </div>

              {expandedCategories['subworkflows'] && (
                <div className="category-functions">
                  {availableSubworkflows.map((subworkflowName) => (
                    <div
                      key={subworkflowName}
                      className="function-item subworkflow-item"
                      draggable
                      onDragStart={(e) => onDragStartSubWorkflow(e, subworkflowName)}
                    >
                      <div className="function-item-icon">
                        <Zap size={14} />
                      </div>
                      <div className="function-item-name">{subworkflowName}</div>
                      <div className="function-item-description">
                        {workflow.subworkflows[subworkflowName].description || 'Sub-workflow call'}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })()}

        {/* Standard Functions Categories - Hidden for composers */}
        {!isComposer && categoriesToDisplay.map((category) => {
          const functions = functionsByCategory[category] || [];
          return (
            <div key={category} className="palette-category">
              <div
                className="category-header"
                onClick={() => toggleCategory(category)}
              >
                {expandedCategories[category] ? (
                  <ChevronDown size={16} />
                ) : (
                  <ChevronRight size={16} />
                )}
                <span>{categoryLabels[category] || category}</span>
                <span className="category-count">{functions.length}</span>
              </div>

              {expandedCategories[category] && (
                <div className="category-functions">
                  {isLoading ? (
                    <div className="no-functions">Loading functions...</div>
                  ) : functions.length === 0 ? (
                    <div className="no-functions">No functions available</div>
                  ) : (
                    functions.map((func) => (
                      <div
                        key={func.name}
                        className="function-item"
                        draggable
                        onDragStart={(e) => onDragStart(e, func)}
                      >
                        <div className="function-item-name">{func.displayName}</div>
                        <div className="function-item-description">
                          {func.description}
                        </div>
                        <div className="function-item-params">
                          {(func.parameters || []).length} parameter{(func.parameters || []).length !== 1 ? 's' : ''}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          );
        })}

        {/* Imported Libraries Section (v2.0 only) - Hidden for composers */}
        {workflow.version === '2.0' && !isComposer && Object.keys(libraryFunctions).length > 0 && (
          <div className="palette-category">
            <div
              className="category-header"
              onClick={() => toggleCategory('libraries')}
            >
              {expandedCategories['libraries'] ? (
                <ChevronDown size={16} />
              ) : (
                <ChevronRight size={16} />
              )}
              <span>Imported Libraries</span>
              <span className="category-count">
                {Object.values(libraryFunctions).reduce((sum, funcs) => sum + funcs.length, 0)}
              </span>
            </div>

            {expandedCategories['libraries'] && (
              <div className="category-content">
                {Object.entries(libraryFunctions).map(([libraryName, functions]) => (
                  <div key={libraryName} className="library-group">
                    <div className="library-group-header">{libraryName}</div>
                    {functions.map((func) => (
                      <div
                        key={`${libraryName}-${func.name}`}
                        className="function-item"
                        draggable
                        onDragStart={(e) => onDragStart(e, {
                          type: 'function',
                          name: func.name,
                          category: func.category,
                          function_file: func.function_file || null,
                          label: func.variant ? `${func.name} (${func.variant})` : func.name
                        })}
                      >
                        <Zap size={14} />
                        <div className="function-info">
                          <div className="function-name">
                            {func.name}
                            {func.variant && <span className="variant-suffix"> ({func.variant})</span>}
                          </div>
                          <div className="function-desc">{func.docstring || 'No description'}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="palette-footer">
        <div className="palette-hint">
          💡 Drag functions to the canvas and customize from node settings
        </div>
      </div>

      {/* Conflict Resolution Dialog */}
      {conflictDialog && (
        <LibraryConflictDialog
          conflicts={conflictDialog.conflicts}
          libraryName={conflictDialog.libraryName}
          onResolve={handleConflictResolution}
          onCancel={() => setConflictDialog(null)}
        />
      )}
    </div>
  );
};

export default FunctionPalette;


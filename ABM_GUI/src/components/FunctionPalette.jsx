import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Database, Zap } from 'lucide-react';
import { getFunctionsByCategoryAsync, FunctionCategory, fetchRegistry } from '../data/functionRegistry';
import useWorkflowStore from '../store/workflowStore';
import './FunctionPalette.css';

/**
 * Function Palette - Sidebar with draggable functions
 */
const FunctionPalette = ({ currentStage }) => {
  const workflow = useWorkflowStore((state) => state.workflow);
  const [functionsByCategory, setFunctionsByCategory] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState({
    [FunctionCategory.INITIALIZATION]: true,
    [FunctionCategory.INTRACELLULAR]: true,
    [FunctionCategory.MICROENVIRONMENT]: true,
    [FunctionCategory.INTERCELLULAR]: true,
    [FunctionCategory.FINALIZATION]: true,
    'subworkflows': true,
  });

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

  return (
    <div className="function-palette">
      <div className="palette-header">
        <h3>Function Library</h3>
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

        {/* Sub-workflows Section (v2.0 only) */}
        {workflow.version === '2.0' && (
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
                {Object.keys(workflow.subworkflows || {}).filter(name => name !== currentStage).length}
              </span>
            </div>

            {expandedCategories['subworkflows'] && (
              <div className="category-functions">
                {Object.keys(workflow.subworkflows || {})
                  .filter(name => name !== currentStage) // Don't show current sub-workflow
                  .map((subworkflowName) => (
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
                {Object.keys(workflow.subworkflows || {}).filter(name => name !== currentStage).length === 0 && (
                  <div className="no-functions">No other sub-workflows available</div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Standard Functions Categories */}
        {categoriesToDisplay.map((category) => {
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
      </div>

      <div className="palette-footer">
        <div className="palette-hint">
          💡 Drag functions to the canvas and customize from node settings
        </div>
      </div>
    </div>
  );
};

export default FunctionPalette;


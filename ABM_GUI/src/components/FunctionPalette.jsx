import { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Database } from 'lucide-react';
import { getFunctionsByCategoryAsync, FunctionCategory, fetchRegistry } from '../data/functionRegistry';
import './FunctionPalette.css';

/**
 * Function Palette - Sidebar with draggable functions
 */
const FunctionPalette = ({ currentStage }) => {
  const [stageFunctions, setStageFunctions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState({
    [FunctionCategory.INITIALIZATION]: true,
    [FunctionCategory.INTRACELLULAR]: true,
    [FunctionCategory.MICROENVIRONMENT]: true,
    [FunctionCategory.INTERCELLULAR]: true,
    [FunctionCategory.FINALIZATION]: true,
  });

  // Load registry on mount and when stage changes
  useEffect(() => {
    const loadFunctions = async () => {
      setIsLoading(true);
      try {
        console.log('[PALETTE] Loading functions for stage:', currentStage);
        const registry = await fetchRegistry();
        console.log('[PALETTE] Registry loaded, total functions:', Object.keys(registry).length);
        const functions = await getFunctionsByCategoryAsync(currentStage);
        console.log('[PALETTE] Functions for stage', currentStage, ':', functions.length);
        setStageFunctions(functions);
      } catch (error) {
        console.error('[PALETTE] Error loading functions:', error);
        setStageFunctions([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadFunctions();
  }, [currentStage]);

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

  const categoryLabels = {
    [FunctionCategory.INITIALIZATION]: 'Initialization',
    [FunctionCategory.INTRACELLULAR]: 'Intracellular',
    [FunctionCategory.MICROENVIRONMENT]: 'Microenvironment',
    [FunctionCategory.INTERCELLULAR]: 'Intercellular',
    [FunctionCategory.FINALIZATION]: 'Finalization',
  };

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

        {/* Standard Functions Category */}
        <div className="palette-category">
          <div
            className="category-header"
            onClick={() => toggleCategory(currentStage)}
          >
            {expandedCategories[currentStage] ? (
              <ChevronDown size={16} />
            ) : (
              <ChevronRight size={16} />
            )}
            <span>{categoryLabels[currentStage]}</span>
            <span className="category-count">{stageFunctions.length}</span>
          </div>

          {expandedCategories[currentStage] && (
            <div className="category-functions">
              {isLoading ? (
                <div className="no-functions">Loading functions...</div>
              ) : stageFunctions.length === 0 ? (
                <div className="no-functions">No functions available</div>
              ) : (
                stageFunctions.map((func) => (
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


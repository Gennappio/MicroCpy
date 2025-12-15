import { useState, useEffect } from 'react';
import { Search, ChevronDown, ChevronRight, Plus, Database } from 'lucide-react';
import { getFunctionsByCategory, FunctionCategory, fetchRegistry } from '../data/functionRegistry';
import './FunctionPalette.css';

/**
 * Function Palette - Sidebar with draggable functions
 */
const FunctionPalette = ({ currentStage }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [customFunctions, setCustomFunctions] = useState([]);
  const [stageFunctions, setStageFunctions] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedCategories, setExpandedCategories] = useState({
    [FunctionCategory.INITIALIZATION]: true,
    [FunctionCategory.INTRACELLULAR]: true,
    [FunctionCategory.MICROENVIRONMENT]: true,
    [FunctionCategory.INTERCELLULAR]: true,
    [FunctionCategory.FINALIZATION]: true,
    custom: true,
  });

  // Load registry on mount and when stage changes
  useEffect(() => {
    const loadFunctions = async () => {
      setIsLoading(true);
      try {
        await fetchRegistry();
        const functions = getFunctionsByCategory(currentStage);
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

  const handleCreateCustomFunction = () => {
    const timestamp = Date.now();
    const newCustomFunction = {
      name: `custom_function_${timestamp}`,
      displayName: `Custom Function ${customFunctions.length + 1}`,
      description: 'Custom workflow function',
      functionFile: 'path/to/function.py',
      isCustom: true,
      parameters: [],
    };
    setCustomFunctions([...customFunctions, newCustomFunction]);
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

  // Filter functions by search term
  const filteredFunctions = stageFunctions.filter(
    (func) =>
      func.displayName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      func.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

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
        <div className="palette-search">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search functions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
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

        {/* Custom Functions Category */}
        {customFunctions.length > 0 && (
          <div className="palette-category">
            <div
              className="category-header custom-category"
              onClick={() => toggleCategory('custom')}
            >
              {expandedCategories.custom ? (
                <ChevronDown size={16} />
              ) : (
                <ChevronRight size={16} />
              )}
              <span>Custom Functions</span>
              <span className="category-count">{customFunctions.length}</span>
            </div>

            {expandedCategories.custom && (
              <div className="category-functions">
                {customFunctions.map((func) => (
                  <div
                    key={func.name}
                    className="function-item custom-function-item"
                    draggable
                    onDragStart={(e) => onDragStart(e, func)}
                  >
                    <div className="function-item-name">{func.displayName}</div>
                    <div className="function-item-description">
                      {func.description}
                    </div>
                    <div className="function-item-file">
                      📄 {func.functionFile}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

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
            <span className="category-count">{filteredFunctions.length}</span>
          </div>

          {expandedCategories[currentStage] && (
            <div className="category-functions">
              {isLoading ? (
                <div className="no-functions">Loading functions...</div>
              ) : filteredFunctions.length === 0 ? (
                <div className="no-functions">No functions available</div>
              ) : (
                filteredFunctions.map((func) => (
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
        <button
          className="btn-create-custom"
          onClick={handleCreateCustomFunction}
        >
          <Plus size={16} />
          Create Custom Function
        </button>
        <div className="palette-hint">
          💡 Drag functions to the canvas and customize from node settings
        </div>
      </div>
    </div>
  );
};

export default FunctionPalette;


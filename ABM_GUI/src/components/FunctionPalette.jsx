import React, { useState } from 'react';
import { Search, ChevronDown, ChevronRight, Plus } from 'lucide-react';
import { getFunctionsByCategory, FunctionCategory } from '../data/functionRegistry';
import CustomFunctionModal from './CustomFunctionModal';
import './FunctionPalette.css';

/**
 * Function Palette - Sidebar with draggable functions
 */
const FunctionPalette = ({ currentStage }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [showCustomModal, setShowCustomModal] = useState(false);
  const [customFunctions, setCustomFunctions] = useState([]);
  const [expandedCategories, setExpandedCategories] = useState({
    [FunctionCategory.INITIALIZATION]: true,
    [FunctionCategory.INTRACELLULAR]: true,
    [FunctionCategory.DIFFUSION]: true,
    [FunctionCategory.INTERCELLULAR]: true,
    [FunctionCategory.FINALIZATION]: true,
    custom: true,
  });

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

  // Get functions for current stage
  const stageFunctions = getFunctionsByCategory(currentStage);

  // Filter functions by search term
  const filteredFunctions = stageFunctions.filter(
    (func) =>
      func.displayName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      func.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const categoryLabels = {
    [FunctionCategory.INITIALIZATION]: 'Initialization',
    [FunctionCategory.INTRACELLULAR]: 'Intracellular',
    [FunctionCategory.DIFFUSION]: 'Diffusion',
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
              {filteredFunctions.length === 0 ? (
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
                      {func.parameters.length} parameter{func.parameters.length !== 1 ? 's' : ''}
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
          onClick={() => setShowCustomModal(true)}
        >
          <Plus size={16} />
          Create Custom Function
        </button>
        <div className="palette-hint">
          💡 Drag functions to the canvas
        </div>
      </div>

      {showCustomModal && (
        <CustomFunctionModal
          onSave={(customFunction) => {
            // Add to custom functions list
            setCustomFunctions([...customFunctions, {
              name: customFunction.functionName,
              displayName: customFunction.displayName,
              description: customFunction.description,
              functionFile: customFunction.functionFile,
              isCustom: true,
              parameters: [], // Will be customized on canvas
            }]);
            setShowCustomModal(false);
          }}
          onClose={() => setShowCustomModal(false)}
        />
      )}
    </div>
  );
};

export default FunctionPalette;


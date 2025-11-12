import React, { useState } from 'react';
import { Search, ChevronDown, ChevronRight } from 'lucide-react';
import { getFunctionsByCategory, FunctionCategory } from '../data/functionRegistry';
import './FunctionPalette.css';

/**
 * Function Palette - Sidebar with draggable functions
 */
const FunctionPalette = ({ currentStage }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedCategories, setExpandedCategories] = useState({
    [FunctionCategory.INITIALIZATION]: true,
    [FunctionCategory.INTRACELLULAR]: true,
    [FunctionCategory.DIFFUSION]: true,
    [FunctionCategory.INTERCELLULAR]: true,
    [FunctionCategory.FINALIZATION]: true,
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
        <div className="palette-hint">
          💡 Drag functions to the canvas
        </div>
      </div>
    </div>
  );
};

export default FunctionPalette;


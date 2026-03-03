import { Layers, Workflow, BarChart3, ListChecks } from 'lucide-react';
import './MainTabSelector.css';

/**
 * MainTabSelector - Top-level navigation between Workflow Designer and Results
 */
const MainTabSelector = ({ currentMainTab, onTabChange }) => {
  return (
    <div className="main-tab-selector">
      {/* Workflow Designer group */}
      <div className="main-tab-group">
        <button
          className={`main-tab ${currentMainTab === 'composers' ? 'active' : ''}`}
          onClick={() => onTabChange('composers')}
        >
          <Layers size={18} />
          <span>Composers</span>
        </button>
        <button
          className={`main-tab ${currentMainTab === 'subworkflows' ? 'active' : ''}`}
          onClick={() => onTabChange('subworkflows')}
        >
          <Workflow size={18} />
          <span>Sub-workflows</span>
        </button>
      </div>

      {/* Planner */}
      <div className="main-tab-group">
        <button
          className={`main-tab planner-tab ${currentMainTab === 'planner' ? 'active' : ''}`}
          onClick={() => onTabChange('planner')}
        >
          <ListChecks size={18} />
          <span>Planner</span>
        </button>
      </div>

      {/* Results */}
      <div className="main-tab-group">
        <button
          className={`main-tab results-tab ${currentMainTab === 'results' ? 'active' : ''}`}
          onClick={() => onTabChange('results')}
        >
          <BarChart3 size={18} />
          <span>Results</span>
        </button>
      </div>
    </div>
  );
};

export default MainTabSelector;


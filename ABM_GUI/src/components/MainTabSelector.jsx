import { Layers, Workflow } from 'lucide-react';
import './MainTabSelector.css';

/**
 * MainTabSelector - Top-level navigation between Composers and Sub-workflows
 */
const MainTabSelector = ({ currentMainTab, onTabChange }) => {
  return (
    <div className="main-tab-selector">
      <button
        className={`main-tab ${currentMainTab === 'composers' ? 'active' : ''}`}
        onClick={() => onTabChange('composers')}
      >
        <Layers size={20} />
        <span>Composers</span>
      </button>
      <button
        className={`main-tab ${currentMainTab === 'subworkflows' ? 'active' : ''}`}
        onClick={() => onTabChange('subworkflows')}
      >
        <Workflow size={20} />
        <span>Sub-workflows</span>
      </button>
    </div>
  );
};

export default MainTabSelector;


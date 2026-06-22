import { Users, Boxes, Globe, PlayCircle, Layers, ListChecks, Sparkles, BarChart3, Network } from 'lucide-react';
import './MainTabSelector.css';

const MainTabSelector = ({ currentMainTab, onTabChange }) => {
  return (
    <div className="main-tab-selector">
      {/* Overview — read-only assembled view of the whole simulation */}
      <div className="main-tab-group">
        <button
          className={`main-tab overview-tab ${currentMainTab === 'overview' ? 'active' : ''}`}
          onClick={() => onTabChange('overview')}
          title="Read-only assembled view of the whole simulation (init → loop → processing)"
        >
          <Network size={18} />
          <span>Overview</span>
        </button>
      </div>

      {/* ABM design tabs */}
      <div className="main-tab-group">
        <button
          className={`main-tab agents-tab ${currentMainTab === 'agents' ? 'active' : ''}`}
          onClick={() => onTabChange('agents')}
          title="Define agent kinds and their behaviors"
        >
          <Users size={18} />
          <span>Agents</span>
        </button>
        <button
          className={`main-tab resources-tab ${currentMainTab === 'resources' ? 'active' : ''}`}
          onClick={() => onTabChange('resources')}
          title="Define resource fields and their Setup/Step behaviours"
        >
          <Boxes size={18} />
          <span>Resources</span>
        </button>
        <button
          className={`main-tab world-tab ${currentMainTab === 'world' ? 'active' : ''}`}
          onClick={() => onTabChange('world')}
          title="Build the world grid (setup_world or a custom grid builder)"
        >
          <Globe size={18} />
          <span>World</span>
        </button>
        <button
          className={`main-tab initialization-tab ${currentMainTab === 'initialization' ? 'active' : ''}`}
          onClick={() => onTabChange('initialization')}
          title="Order the init behaviours that run once at the start"
        >
          <PlayCircle size={18} />
          <span>Initialization</span>
        </button>
        <button
          className={`main-tab scheduler-tab ${currentMainTab === 'scheduler' ? 'active' : ''}`}
          onClick={() => onTabChange('scheduler')}
          title="Order behaviors into the main simulation loop"
        >
          <Layers size={18} />
          <span>Scheduler</span>
        </button>
      </div>

      {/* Planner */}
      <div className="main-tab-group">
        <button
          className={`main-tab planner-tab ${currentMainTab === 'planner' ? 'active' : ''}`}
          onClick={() => onTabChange('planner')}
          title="Configure simulation parameters and batch runs"
        >
          <ListChecks size={18} />
          <span>Planner</span>
        </button>
      </div>

      {/* Processing & Results */}
      <div className="main-tab-group">
        <button
          className={`main-tab processing-tab ${currentMainTab === 'processing' ? 'active' : ''}`}
          onClick={() => onTabChange('processing')}
          title="Define post-simulation processing behaviors"
        >
          <Sparkles size={18} />
          <span>Processing</span>
        </button>
        <button
          className={`main-tab results-tab ${currentMainTab === 'results' ? 'active' : ''}`}
          onClick={() => onTabChange('results')}
          title="View simulation results and plots"
        >
          <BarChart3 size={18} />
          <span>Results</span>
        </button>
      </div>
    </div>
  );
};

export default MainTabSelector;

import { useState, useEffect } from 'react';
import { Image, RefreshCw, ChevronDown } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import './WorkflowResults.css';

const API_BASE_URL = 'http://localhost:5001';

/**
 * WorkflowResults - Per-subworkflow results viewer (v2.0 nested structure)
 */
function WorkflowResults({ subworkflowName, subworkflowKind }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedPlot, setSelectedPlot] = useState(null);
  const [availablePlots, setAvailablePlots] = useState([]);

  // Subscribe to simulation run counter to auto-refresh when a new run starts
  const simulationRunCounter = useWorkflowStore((state) => state.simulationRunCounter);

  useEffect(() => {
    loadResults();
  }, [subworkflowName, subworkflowKind, simulationRunCounter]);

  const loadResults = async () => {
    setLoading(true);
    setError('');
    try {
      // Fetch results for this specific subworkflow (v2.0 nested structure)
      const url = `${API_BASE_URL}/api/results/list?subworkflow_name=${encodeURIComponent(subworkflowName)}&subworkflow_kind=${encodeURIComponent(subworkflowKind)}`;
      console.log('[WorkflowResults] Fetching:', url);
      const res = await fetch(url);
      const data = await res.json();
      console.log('[WorkflowResults] Response:', data);
      console.log('[WorkflowResults] Plots count:', data.plots?.length || 0);

      if (data.success) {
        setAvailablePlots(data.plots || []);
        console.log('[WorkflowResults] Set availablePlots:', data.plots?.length || 0);

        // Auto-select the first plot
        if (data.plots && data.plots.length > 0) {
          setSelectedPlot(data.plots[0]);
          console.log('[WorkflowResults] Auto-selected first plot:', data.plots[0]?.name);
        } else {
          setSelectedPlot(null);
        }
      } else {
        setError(data.error || 'Failed to load results');
      }
    } catch (err) {
      console.error('Error loading results:', err);
      setError(`Failed to load results: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handlePlotSelect = (e) => {
    const plotPath = e.target.value;
    const plot = availablePlots.find(p => p.path === plotPath);
    setSelectedPlot(plot);
  };

  return (
    <div className="workflow-results">
      {/* Results Header with Dropdown */}
      <div className="results-header">
        <div className="results-title">
          <Image size={16} />
          <span>Results</span>
        </div>
        
        <div className="results-controls">
          <button 
            className="btn-refresh" 
            onClick={loadResults} 
            disabled={loading}
            title="Refresh results"
          >
            <RefreshCw size={12} className={loading ? 'spinning' : ''} />
          </button>
        </div>
      </div>

      {/* Dropdown Menu */}
      <div className="results-dropdown">
        <select 
          className="plot-selector"
          value={selectedPlot?.path || ''}
          onChange={handlePlotSelect}
          disabled={availablePlots.length === 0}
        >
          {availablePlots.length === 0 ? (
            <option value="">No results available</option>
          ) : (
            <>
              <option value="">Select a plot...</option>
              {availablePlots.map(plot => (
                <option key={plot.path} value={plot.path}>
                  {plot.category} - {plot.name}
                </option>
              ))}
            </>
          )}
        </select>
        <ChevronDown size={14} className="dropdown-icon" />
      </div>

      {/* Plot Viewer */}
      <div className="results-viewer">
        {error && (
          <div className="results-error">
            <p>{error}</p>
          </div>
        )}
        
        {loading ? (
          <div className="results-empty">
            <RefreshCw size={32} className="spinning" opacity={0.3} />
            <p>Loading results...</p>
          </div>
        ) : selectedPlot ? (
          <div className="plot-display">
            <img 
              src={`${API_BASE_URL}/api/results/plot/${selectedPlot.path}`}
              alt={selectedPlot.name}
              className="plot-image"
            />
          </div>
        ) : (
          <div className="results-empty">
            <Image size={32} opacity={0.3} />
            <p>No plot selected</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default WorkflowResults;


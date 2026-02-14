import { useState, useEffect } from 'react';
import { Image, RefreshCw, ChevronDown } from 'lucide-react';
import './WorkflowResults.css';

const API_BASE_URL = 'http://localhost:5001';

/**
 * WorkflowResults - Per-subworkflow results viewer (v2.0 nested structure)
 * Images only refresh when the Refresh button is clicked to reduce UI clutter during simulation runs.
 */
function WorkflowResults({ subworkflowName, subworkflowKind }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedPlot, setSelectedPlot] = useState(null);
  const [availablePlots, setAvailablePlots] = useState([]);
  // Timestamp used to cache-bust images - only updated on manual refresh
  const [imageTimestamp, setImageTimestamp] = useState(Date.now());

  // Only load results on initial mount or when subworkflow changes
  useEffect(() => {
    loadResults();
  }, [subworkflowName, subworkflowKind]);

  const loadResults = async () => {
    setLoading(true);
    setError('');
    // Update timestamp to force image refresh
    setImageTimestamp(Date.now());
    try {
      // Fetch results from GUI_results directory
      const url = `${API_BASE_URL}/api/results/list`;
      console.log('[WorkflowResults] Fetching:', url);
      const res = await fetch(url);
      const data = await res.json();
      console.log('[WorkflowResults] Response:', data);

      if (data.success) {
        // Flatten all plots from all result groups
        const allPlots = (data.results || []).flatMap(r => r.plots || []);
        console.log('[WorkflowResults] Plots count:', allPlots.length);
        setAvailablePlots(allPlots);

        // Auto-select the first plot
        if (allPlots.length > 0) {
          setSelectedPlot(allPlots[0]);
          console.log('[WorkflowResults] Auto-selected first plot:', allPlots[0]?.name);
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
              src={`${API_BASE_URL}/api/results/plot/${selectedPlot.path}?t=${imageTimestamp}`}
              alt={selectedPlot.name}
              className="plot-image"
              key={`${selectedPlot.path}-${imageTimestamp}`}
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


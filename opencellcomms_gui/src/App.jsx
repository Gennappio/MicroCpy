import { useState, useEffect } from 'react';
import { Download, Upload, FileJson, Save } from 'lucide-react';
import MainTabSelector from './components/MainTabSelector';
import ResultsExplorer from './components/ResultsExplorer';
import PlannerView from './components/PlannerView';
import AgentsView from './components/AgentsView';
import EnvironmentView from './components/EnvironmentView';
import InitSequenceView from './components/InitSequenceView';
import SchedulerView from './components/SchedulerView';
import ProcessingView from './components/ProcessingView';
import useWorkflowStore from './store/workflowStore';
import { fetchRegistry } from './data/functionRegistry';
import './App.css';

function App() {
	  const {
    currentMainTab,
    setCurrentMainTab,
    workflow,
    loadWorkflow,
    exportWorkflow,
    setWorkflowFilePath,
    workflowFilePath,
  } = useWorkflowStore();

  // Resizable panel widths
  const [paletteWidth, setPaletteWidth] = useState(308);  // Increased by 10% (280 * 1.1 = 308)
  const [inspectorWidth, setInspectorWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(null);

  // Resize handlers
  const handleMouseDown = (panel) => (e) => {
    e.preventDefault();
    setIsResizing(panel);
  };

  useEffect(() => {
    if (!isResizing) {
      document.body.classList.remove('resizing');
      return;
    }

    document.body.classList.add('resizing');

    const handleMouseMove = (e) => {
      if (isResizing === 'palette') {
        // Palette: min 250px, max matches content width (no arbitrary limit)
        const newWidth = Math.max(250, Math.min(400, e.clientX));
        setPaletteWidth(newWidth);
      } else if (isResizing === 'inspector') {
        const newWidth = Math.max(280, Math.min(600, window.innerWidth - e.clientX));
        setInspectorWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(null);
      document.body.classList.remove('resizing');
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.classList.remove('resizing');
    };
  }, [isResizing]);

  // Preload function registry on app mount
  useEffect(() => {
    fetchRegistry().then(() => {
      console.log('[APP] Function registry loaded');
    }).catch((error) => {
      console.error('[APP] Failed to load function registry:', error);
    });
  }, []);

  // When main tab changes, switch to first available subworkflow of that kind
  // Stage switching is handled inside each tab view component.

  const handleImportWorkflow = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          try {
            const workflowData = JSON.parse(event.target.result);
            // Pass file path for library path resolution (Phase 6)
            // Note: file.path is only available in Electron, not in browser
            // Use file.name as fallback so Save button appears
            const filePath = file.path || file.name;
            loadWorkflow(workflowData, filePath);
            alert(`Workflow "${workflowData.name}" loaded successfully!`);
          } catch (error) {
            alert('Error loading workflow: ' + error.message);
          }
        };
        reader.readAsText(file);
      }
    };
    input.click();
  };

  const handleExportWorkflow = () => {
    // Phase 6: Prompt for workflow directory to enable relative path handling
    // Note: In browser, we can't get the actual save path, so we ask the user
    let workflowDir = null;

    if (workflow.metadata?.gui?.function_libraries?.length > 0) {
      workflowDir = prompt(
        'Enter the directory where you will save this workflow file:\n' +
        '(This is needed to make library paths relative)\n\n' +
        'Example: /Users/yourname/projects/workflows\n' +
        'or C:\\Users\\yourname\\projects\\workflows',
        ''
      );

      if (workflowDir) {
        // Store the workflow file path (directory + filename)
        const filename = `${workflow.name.replace(/\s+/g, '_').toLowerCase()}.json`;
        const fullPath = `${workflowDir}/${filename}`;
        setWorkflowFilePath(fullPath);
      }
    }

    const workflowData = exportWorkflow();
    const blob = new Blob([JSON.stringify(workflowData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${workflow.name.replace(/\s+/g, '_').toLowerCase()}.json`;
    a.click();
    URL.revokeObjectURL(url);

    if (workflowDir) {
      alert(
        'Workflow exported!\n\n' +
        'Library paths have been made relative to the workflow directory.\n' +
        'Make sure to save the file in the directory you specified.'
      );
    }
  };

  // Store file handle for direct saving (File System Access API)
  const [fileHandle, setFileHandle] = useState(null);

  const handleSaveWorkflow = async () => {
    // Ask for confirmation before saving
    const confirmed = window.confirm(
      `Are you sure you want to save the current project?\n\n` +
      `File: ${workflowFilePath || 'New file'}\n\n` +
      `This will overwrite the existing file.`
    );

    if (!confirmed) {
      return;
    }

    try {
      const workflowData = exportWorkflow();
      const jsonContent = JSON.stringify(workflowData, null, 2);

      console.log('[SAVE] Workflow data to save:', workflowData);
      console.log('[SAVE] JSON content length:', jsonContent.length);

      // If we have a file handle from a previous save, use it
      if (fileHandle) {
        try {
          console.log('[SAVE] Using existing file handle:', fileHandle.name);
          const writable = await fileHandle.createWritable();
          await writable.write(jsonContent);
          await writable.close();
          console.log('[SAVE] Successfully wrote to file');
          alert(`Project saved successfully!\n\nFile: ${fileHandle.name}`);
          return;
        } catch (err) {
          console.log('[SAVE] Could not write to existing handle:', err);
        }
      }

      // Use File System Access API to let user pick save location
      if ('showSaveFilePicker' in window) {
        console.log('[SAVE] Using File System Access API');
        try {
          const handle = await window.showSaveFilePicker({
            suggestedName: workflowFilePath || `${workflow.name.replace(/\s+/g, '_').toLowerCase()}.json`,
            types: [{
              description: 'JSON Files',
              accept: { 'application/json': ['.json'] }
            }]
          });

          console.log('[SAVE] Got file handle:', handle.name);

          const writable = await handle.createWritable();
          await writable.write(jsonContent);
          await writable.close();

          console.log('[SAVE] Successfully wrote to new file');

          // Store the handle for future saves
          setFileHandle(handle);
          setWorkflowFilePath(handle.name);

          alert(`Project saved successfully!\n\nFile: ${handle.name}`);
        } catch (err) {
          if (err.name !== 'AbortError') {
            console.error('[SAVE] Save failed:', err);
            alert('Error saving project: ' + err.message);
          } else {
            console.log('[SAVE] User cancelled save dialog');
          }
        }
      } else {
        console.log('[SAVE] File System Access API not available, using download fallback');
        // Fallback for browsers without File System Access API
        const blob = new Blob([jsonContent], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = workflowFilePath || `${workflow.name.replace(/\s+/g, '_').toLowerCase()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        alert('Project downloaded. Please replace the original file manually.');
      }
    } catch (error) {
      console.error('[SAVE] Error:', error);
      alert('Error saving project: ' + error.message);
    }
  };






  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-left">
          <FileJson size={24} className="logo-icon" />
          <div className="header-title">
            <h1>OpenCellComms</h1>
            <p>{workflow.name}</p>
          </div>
        </div>

        <div className="header-actions">
          <button className="btn btn-secondary" onClick={handleImportWorkflow}>
            <Upload size={16} />
            Import Project
          </button>
          <button
            className="btn btn-success"
            onClick={handleSaveWorkflow}
            disabled={!workflowFilePath}
            title={workflowFilePath ? `Save to: ${workflowFilePath}` : 'Import a project first'}
          >
            <Save size={16} />
            Save Project
          </button>
          <button className="btn btn-primary" onClick={handleExportWorkflow}>
            <Download size={16} />
            Export Project
          </button>
        </div>
      </header>

      {/* Main Tab Selector */}
      <MainTabSelector
        currentMainTab={currentMainTab}
        onTabChange={setCurrentMainTab}
      />

      {/* === ABM Tab Views === */}
      {currentMainTab === 'agents' && (
        <AgentsView
          paletteWidth={paletteWidth}
          inspectorWidth={inspectorWidth}
          onMouseDownPalette={handleMouseDown('palette')}
          onMouseDownInspector={handleMouseDown('inspector')}
        />
      )}

      {currentMainTab === 'environment' && (
        <EnvironmentView
          paletteWidth={paletteWidth}
          inspectorWidth={inspectorWidth}
          onMouseDownPalette={handleMouseDown('palette')}
          onMouseDownInspector={handleMouseDown('inspector')}
        />
      )}

      {currentMainTab === 'initialization' && (
        <InitSequenceView
          paletteWidth={paletteWidth}
          inspectorWidth={inspectorWidth}
          onMouseDownPalette={handleMouseDown('palette')}
          onMouseDownInspector={handleMouseDown('inspector')}
        />
      )}

      {currentMainTab === 'scheduler' && (
        <SchedulerView
          paletteWidth={paletteWidth}
          inspectorWidth={inspectorWidth}
          onMouseDownPalette={handleMouseDown('palette')}
          onMouseDownInspector={handleMouseDown('inspector')}
        />
      )}

      {currentMainTab === 'processing' && (
        <ProcessingView
          paletteWidth={paletteWidth}
          inspectorWidth={inspectorWidth}
          onMouseDownPalette={handleMouseDown('palette')}
          onMouseDownInspector={handleMouseDown('inspector')}
        />
      )}

      {currentMainTab === 'planner' && (
        <div className="fullpage-content">
          <PlannerView />
        </div>
      )}

      {currentMainTab === 'results' && (
        <div className="fullpage-content">
          <ResultsExplorer />
        </div>
      )}

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-info">
          <span>Version: {workflow.version}</span>
        </div>
        <div className="footer-hint">
          Agents → Environment → Scheduler → Planner → Processing → Results
        </div>
      </footer>
    </div>
  );
}

export default App;

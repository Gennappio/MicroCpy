import { useEffect, useState, useRef } from 'react';
import { ChevronDown, ChevronRight, Database, List, Braces, Plus, FolderOpen, FileJson, X, Package } from 'lucide-react';
import { fetchRegistry } from '../data/functionRegistry';
import useWorkflowStore from '../store/workflowStore';
import NewFunctionDialog from './NewFunctionDialog';
import { FUNCTION_HOSTING_KINDS, KINDS } from '../store/subworkflowKinds';
import {
  contractForFunction,
  contractForSubworkflow,
} from '../utils/contractUtils';
import './FunctionPalette.css';

const DEFAULT_FUNCTIONS_BY_KIND = {
  [KINDS.WORLD]: ['setup_world', 'plot_world'],
  [KINDS.AGENT_INIT]: ['plot_agents'],
  [KINDS.RESOURCE_INIT]: ['plot_resources'],
};

/**
 * Function Palette - empty by default. Users load functions from workflow JSONs
 * or create new ones inline.
 */
const FunctionPalette = ({ currentStage }) => {
  const workflow = useWorkflowStore((state) => state.workflow);
  const addWorkflowLibrary = useWorkflowStore((state) => state.addWorkflowLibrary);
  const removeFunctionLibrary = useWorkflowStore((state) => state.removeFunctionLibrary);
  const addUserFunction = useWorkflowStore((state) => state.addUserFunction);
  const removeUserFunction = useWorkflowStore((state) => state.removeUserFunction);
  const importSubworkflow = useWorkflowStore((state) => state.importSubworkflow);

  const [expanded, setExpanded] = useState({});
  const [showNewFunc, setShowNewFunc] = useState(false);
  const [registryCache, setRegistryCache] = useState({});
  const [plugins, setPlugins] = useState([]);
  const [pluginMenuOpen, setPluginMenuOpen] = useState(false);
  const [loadingPlugins, setLoadingPlugins] = useState(false);
  const workflowFileRef = useRef(null);

  const currentKind = workflow.metadata?.gui?.subworkflow_kinds?.[currentStage];
  const currentSubworkflow = workflow.subworkflows?.[currentStage];
  const currentContract = contractForSubworkflow(currentSubworkflow, currentKind);
  const canHostFunctions = FUNCTION_HOSTING_KINDS.has(currentKind);
  const isSchedulerCanvas = currentKind === KINDS.SCHEDULER;
  const defaultFunctions = DEFAULT_FUNCTIONS_BY_KIND[currentKind] || [];

  const libraries = workflow.metadata?.gui?.function_libraries || [];
  const userFunctions = workflow.metadata?.gui?.user_functions || [];

  // Lazy registry fetch (cached) for parameter metadata lookups
  const ensureRegistry = async () => {
    if (Object.keys(registryCache).length > 0) return registryCache;
    const reg = await fetchRegistry();
    setRegistryCache(reg || {});
    return reg || {};
  };

  useEffect(() => {
    if (defaultFunctions.length > 0) {
      ensureRegistry();
    }
  }, [currentKind]);

  // ─── Drag handlers ──────────────────────────────────────────────────────

  const onDragStart = (event, functionData) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify(functionData));
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDragStartParameter = (event) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({
      type: 'parameterNode', label: 'New Parameters', parameters: {},
    }));
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDragStartList = (event, listType) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({
      type: 'listParameterNode',
      label: `${listType === 'float' ? 'Float' : 'String'} List`,
      listType, items: [],
    }));
    event.dataTransfer.effectAllowed = 'move';
  };

  const onDragStartDict = (event) => {
    event.dataTransfer.setData('application/reactflow', JSON.stringify({
      type: 'dictParameterNode', label: 'Dictionary', entries: [],
    }));
    event.dataTransfer.effectAllowed = 'move';
  };

  // ─── Load from workflow JSON ────────────────────────────────────────────

  const handleLoadWorkflow = () => workflowFileRef.current?.click();

  const handleWorkflowFileSelected = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const data = JSON.parse(text);

      // ── Standalone behavior file (.subworkflow.json) ──────────────────
      // These are written by "Export Behavior" (format: 'subworkflow'). Import
      // the whole behavior as its own canvas, rather than treating it like a
      // function library.
      if (data.format === 'subworkflow') {
        const swName =
          data.name || file.name.replace(/\.subworkflow\.json$/i, '').replace(/\.json$/i, '');
        const swKind = data.kind;

        // Warn (non-blocking) if the behavior's role doesn't match the canvas
        // the user is currently on — e.g. loading an env_behavior while viewing
        // an agent canvas.
        if (currentKind && swKind && swKind !== currentKind) {
          const ok = window.confirm(
            `This behavior is a "${swKind}", but you're on a "${currentKind}" canvas.\n\n` +
            `Import it anyway as a new "${swKind}" behavior?`
          );
          if (!ok) {
            e.target.value = '';
            return;
          }
        }

        const ok = importSubworkflow(swName, data, swKind);
        if (!ok) {
          alert(
            `Could not import behavior "${swName}" — a behavior with that name already exists in this project.`
          );
        } else {
          await ensureRegistry();
        }
        e.target.value = '';
        return;
      }

      // ── Full workflow file ────────────────────────────────────────────
      // Extract function names from all subworkflows
      const fnNames = new Set();
      Object.values(data.subworkflows || {}).forEach((sw) => {
        (sw.functions || []).forEach((f) => {
          if (f.function_name) fnNames.add(f.function_name);
        });
      });

      if (fnNames.size === 0) {
        // Tell the user *why* it's empty rather than blaming "no functions".
        if (!data.subworkflows) {
          alert(
            'This file is not a workflow or behavior file (no "subworkflows" and no behavior found).'
          );
        } else {
          alert('No functions found in this workflow file.');
        }
        e.target.value = '';
        return;
      }

      const path = file.path || file.name;
      addWorkflowLibrary(data.name || file.name, path, Array.from(fnNames));
      // Make sure registry is loaded so we can show metadata
      await ensureRegistry();
    } catch (err) {
      alert('Failed to load file: ' + err.message);
    }
    e.target.value = '';
  };

  // ─── Load a plugin's functions into the palette ─────────────────────────
  // The backend already lists every installed plugin and the functions it
  // registers (/api/plugins). Loading one drops its functions into the palette
  // via the same library mechanism used for workflow files, so they're instantly
  // draggable onto the canvas.

  const handleTogglePluginMenu = async () => {
    if (!pluginMenuOpen) {
      setLoadingPlugins(true);
      try {
        const res = await fetch('http://localhost:5001/api/plugins');
        const data = await res.json();
        // `common` is shared infrastructure, not an experiment plugin.
        if (data.success) setPlugins((data.plugins || []).filter((p) => p.name !== 'common'));
      } catch {
        /* leave the list empty — the menu shows a "no plugins" hint */
      } finally {
        setLoadingPlugins(false);
      }
    }
    setPluginMenuOpen((open) => !open);
  };

  const handleLoadPlugin = async (plugin) => {
    setPluginMenuOpen(false);
    if (!plugin.functions || plugin.functions.length === 0) {
      alert(`Plugin "${plugin.name}" has no registered functions yet.`);
      return;
    }
    addWorkflowLibrary(plugin.name, plugin.path, plugin.functions);
    // Always pull a fresh registry so just-created functions show metadata.
    const reg = await fetchRegistry();
    setRegistryCache(reg || {});
  };

  // ─── Create new function (staging only — no file written yet) ──────────

  const handleCreateFunction = (def) => {
    // Just stage the function in metadata.gui.user_functions. The actual
    // Python file is written later when the user clicks Export Behavior on
    // the canvas. This lets users edit/discard before committing to disk.
    addUserFunction({
      name: def.name,
      file_path: def.file_path,
      behavior: currentStage,
      parameters: def.parameters,
      category: def.category,
      kind: def.kind,
      requires: def.requires,
      typed_env_exempt: def.typed_env_exempt,
      contract: def.contract,
      exported: false,
    });
    setShowNewFunc(false);
  };

  // ─── Sub-workflow palette section (cross-canvas calls) ─────────────────

  const buildSubworkflowCallData = (name) => ({
    type: 'subworkflowCall', subworkflowName: name, label: name, iterations: 1, parameters: {},
  });

  const showSubworkflowCalls = currentKind === KINDS.COMPOSER || currentKind === KINDS.SUBWORKFLOW;

  const toggle = (key) => setExpanded((s) => ({ ...s, [key]: !s[key] }));
  const isExpanded = (key, defaultOpen = true) => expanded[key] !== undefined ? expanded[key] : defaultOpen;

  // ─── Function item render helper ────────────────────────────────────────

  const renderFunctionItem = (name, source = null) => {
    const meta = registryCache[name];
    const userFn = userFunctions.find((f) => f.name === name);
    const isStaged = source === 'user' && userFn && userFn.exported === false;

    // For staged functions: use the user's declared parameters (file doesn't exist yet).
    // For exported/library functions: use registry metadata.
    const description = meta?.description
      || (isStaged ? '✱ unsaved — click Export Behavior to write the file' : 'No description');
    const paramList = isStaged
      ? (userFn?.parameters || [])
      : (meta?.parameters || []);
    const paramCount = paramList.length;
    const contract = contractForFunction(meta, userFn, currentKind, currentContract);

    // Draggable payload — even staged functions can be dragged onto the canvas.
    // The function_name + parameters travel with the drag.
    const payload = {
      type: 'function',
      name,
      function_name: name,
      label: meta?.displayName || name,
      displayName: meta?.displayName || name,
      description,
      category: meta?.category,
      contract,
      parameters: paramList.reduce((acc, p) => { acc[p.name] = p.default; return acc; }, {}),
    };

    // Draggable as long as we have either backend metadata OR a staged spec
    const draggable = !!meta || isStaged;
    const title = isStaged
      ? '✱ unsaved — drag onto canvas, then click Export Behavior to write the file'
      : (!meta ? 'Not loaded in backend registry yet — restart backend or open the originating workflow' : '');

    return (
      <div
        key={`${source || 'lib'}-${name}`}
        className={`function-item ${!meta && !isStaged ? 'unloaded' : ''} ${isStaged ? 'unsaved' : ''}`}
        draggable={draggable}
        title={title}
        onDragStart={draggable ? (e) => onDragStart(e, payload) : undefined}
      >
        <div className="function-item-name">
          {isStaged && <span className="unsaved-marker" title="Not yet exported">✱</span>}
          {name}
        </div>
        <div className="function-item-description">{description}</div>
        <div className="function-item-params">
          {paramCount} parameter{paramCount !== 1 ? 's' : ''}
        </div>
      </div>
    );
  };

  // ─── Render ─────────────────────────────────────────────────────────────

  const hasContent = defaultFunctions.length > 0 || libraries.length > 0 || userFunctions.length > 0;

  return (
    <div className="function-palette">
      <div className="palette-header">
        <h3>Library</h3>
      </div>

      <div className="palette-actions-bar">
        <button
          className="palette-pri-btn"
          onClick={handleLoadWorkflow}
          title="Load functions from a workflow or behavior (.json / .subworkflow.json) file"
        >
          <FolderOpen size={14} />
          Load File
        </button>
        <div className="palette-plugin-wrap">
          <button
            className="palette-pri-btn"
            onClick={handleTogglePluginMenu}
            title="Load all functions from an installed plugin"
          >
            <Package size={14} />
            Plugin
            <ChevronDown size={12} />
          </button>
          {pluginMenuOpen && (
            <div className="palette-plugin-menu">
              {loadingPlugins && <div className="palette-plugin-empty">Loading plugins…</div>}
              {!loadingPlugins && plugins.length === 0 && (
                <div className="palette-plugin-empty">No plugins found</div>
              )}
              {!loadingPlugins && plugins.map((p) => (
                <button
                  key={p.name}
                  className="palette-plugin-item"
                  onClick={() => handleLoadPlugin(p)}
                  title={p.path}
                >
                  <span className="pp-name">{p.name}</span>
                  <span className="pp-count">{p.functions?.length || 0}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          className="palette-pri-btn"
          onClick={() => setShowNewFunc(true)}
          disabled={!canHostFunctions}
          title={canHostFunctions ? 'Create a new function for this canvas' : 'Open a behavior or init canvas to create functions'}
        >
          <Plus size={14} />
          New
        </button>
        <input
          ref={workflowFileRef}
          type="file"
          accept=".json"
          style={{ display: 'none' }}
          onChange={handleWorkflowFileSelected}
        />
      </div>

      <div className="palette-content">

        {/* Parameter helper nodes — always available */}
        <div className="parameter-node-section">
          <div className="parameter-node-header">
            <Database size={16} />
            <span>Parameters</span>
          </div>

          <div className="parameter-node-draggable" draggable onDragStart={onDragStartParameter}>
            <Database size={14} />
            <div className="parameter-node-info">
              <div className="parameter-node-name">Key-Value</div>
              <div className="parameter-node-desc">Simple parameter storage</div>
            </div>
          </div>

          <div className="parameter-node-draggable list-string" draggable onDragStart={(e) => onDragStartList(e, 'string')}>
            <List size={14} />
            <div className="parameter-node-info">
              <div className="parameter-node-name">List [String]</div>
              <div className="parameter-node-desc">List of strings</div>
            </div>
          </div>

          <div className="parameter-node-draggable list-float" draggable onDragStart={(e) => onDragStartList(e, 'float')}>
            <List size={14} />
            <div className="parameter-node-info">
              <div className="parameter-node-name">List [Float]</div>
              <div className="parameter-node-desc">List of numeric values</div>
            </div>
          </div>

          <div className="parameter-node-draggable dict" draggable onDragStart={onDragStartDict}>
            <Braces size={14} />
            <div className="parameter-node-info">
              <div className="parameter-node-name">Dictionary</div>
              <div className="parameter-node-desc">Key-value with typed values</div>
            </div>
          </div>
        </div>

        {/* Default nodes for this canvas kind */}
        {defaultFunctions.length > 0 && (
          <div className="palette-category">
            <div className="category-header" onClick={() => toggle('defaults')}>
              {isExpanded('defaults') ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <span>Defaults</span>
              <span className="category-count">{defaultFunctions.length}</span>
            </div>
            {isExpanded('defaults') && (
              <div className="category-functions">
                {defaultFunctions.map((name) => renderFunctionItem(name, 'default'))}
              </div>
            )}
          </div>
        )}

        {/* Legacy composer-only subworkflow calls. ABM orchestration uses the dedicated Initialization and Scheduler palettes. */}
        {showSubworkflowCalls && !isSchedulerCanvas && Object.keys(workflow.subworkflows || {}).filter((n) => n !== currentStage).length > 0 && (
          <div className="palette-category">
            <div className="category-header" onClick={() => toggle('subworkflows')}>
              {isExpanded('subworkflows') ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <span>Sub-workflow Calls</span>
            </div>
            {isExpanded('subworkflows') && (
              <div className="category-functions">
                {Object.keys(workflow.subworkflows || {}).filter((n) => n !== currentStage).map((name) => {
                  const kind = workflow.metadata?.gui?.subworkflow_kinds?.[name];
                  if (kind === KINDS.SCHEDULER) return null;
                  return (
                    <div
                      key={name}
                      className="function-item subworkflow-item"
                      draggable
                      onDragStart={(e) => onDragStart(e, buildSubworkflowCallData(name))}
                    >
                      <div className="function-item-name">{name}</div>
                      <div className="function-item-description">
                        {workflow.subworkflows[name]?.description || kind || ''}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Project (user-created) functions */}
        {userFunctions.length > 0 && (
          <div className="palette-category">
            <div className="category-header" onClick={() => toggle('project')}>
              {isExpanded('project') ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <span>Project</span>
              <span className="category-count">{userFunctions.length}</span>
            </div>
            {isExpanded('project') && (
              <div className="category-functions">
                {userFunctions.map((uf) => {
                  const item = renderFunctionItem(uf.name, 'user');
                  if (!item) return null;
                  return (
                    <div key={`u-${uf.name}`} className="function-item-row">
                      <div className="function-item-wrap">
                        {item}
                      </div>
                      <button
                        className="function-item-remove"
                        title="Remove from project (does not delete file)"
                        onClick={() => removeUserFunction(uf.name)}
                      >
                        <X size={12} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Each loaded workflow library */}
        {libraries.filter((l) => l.type === 'workflow').map((lib) => (
          <div className="palette-category" key={lib.path}>
            <div className="category-header library-header" onClick={() => toggle(`lib-${lib.path}`)}>
              {isExpanded(`lib-${lib.path}`) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <FileJson size={14} />
              <div className="library-header-text">
                <div className="library-name">{lib.name}</div>
                <div className="library-path" title={lib.path}>{lib.path}</div>
              </div>
              <button
                className="function-item-remove"
                title="Remove library"
                onClick={(e) => { e.stopPropagation(); removeFunctionLibrary(lib.path); }}
              >
                <X size={12} />
              </button>
            </div>
            {isExpanded(`lib-${lib.path}`) && (
              <div className="category-functions">
                {(lib.functions || []).map((name) => renderFunctionItem(name, lib.path))}
              </div>
            )}
          </div>
        ))}

        {/* Empty state */}
        {!hasContent && (
          <div className="palette-empty">
            <FolderOpen size={36} opacity={0.3} />
            <p>No functions loaded.</p>
            <p className="palette-empty-hint">
              Load functions from another workflow, or create a new one (only on behavior canvases).
            </p>
          </div>
        )}
      </div>

      {showNewFunc && (
        <NewFunctionDialog
          behaviorName={currentStage}
          currentKind={currentKind}
          currentContract={currentContract}
          onCreate={handleCreateFunction}
          onCancel={() => setShowNewFunc(false)}
        />
      )}
    </div>
  );
};

export default FunctionPalette;

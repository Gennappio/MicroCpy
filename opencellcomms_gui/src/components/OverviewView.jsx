import { useMemo, useEffect } from 'react';
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Network, Lock } from 'lucide-react';
import useWorkflowStore from '../store/workflowStore';
import { buildOverviewModel } from '../utils/overviewModel';
import { assembleLiveWorkflow } from '../utils/assembleWorkflow';
import { OverviewNode, OverviewHeader } from './OverviewNode';
import './OverviewView.css';

// Module scope: a stable nodeTypes object (React Flow warns if it changes each render).
const nodeTypes = {
  overviewNode: OverviewNode,
  overviewHeader: OverviewHeader,
};

const OverviewView = () => {
  // Build from the LIVE canvas state (stageNodes/stageEdges), not the stored
  // subworkflows cache — so the Overview reflects edits the instant you make
  // them, using the same assembly path as export.
  const workflow = useWorkflowStore((s) => s.workflow);
  const stageNodes = useWorkflowStore((s) => s.stageNodes);
  const stageEdges = useWorkflowStore((s) => s.stageEdges);
  const model = useMemo(
    () => buildOverviewModel(assembleLiveWorkflow(workflow, stageNodes, stageEdges)),
    [workflow, stageNodes, stageEdges],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(model.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(model.edges);

  // Keep the read-only canvas in sync when the workflow changes on another tab.
  useEffect(() => {
    setNodes(model.nodes);
    setEdges(model.edges);
  }, [model, setNodes, setEdges]);

  return (
    <div className="overview-view">
      <div className="overview-banner">
        <Network size={18} className="overview-banner-icon" />
        <div className="overview-banner-text">
          <strong>Overview · read-only.</strong> The whole simulation assembled in
          execution order — your behaviours plus the engine's locked reconciliation
          pipeline. Nothing here is editable; click a behaviour to open its canvas.
        </div>
        <div className="overview-legend">
          <span className="legend-item"><span className="legend-swatch authored" /> Authored</span>
          <span className="legend-item"><Lock size={11} /> System (locked)</span>
        </div>
      </div>

      <div className="overview-canvas">
        {model.empty ? (
          <div className="overview-empty">{model.reason || 'Nothing to show yet.'}</div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable
            edgesUpdatable={false}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.2}
            proOptions={{ hideAttribution: false }}
          >
            <Background variant={BackgroundVariant.Dots} gap={18} size={1} color="#e2e8f0" />
            <Controls showInteractive={false} />
            <MiniMap pannable zoomable nodeStrokeWidth={2} />
          </ReactFlow>
        )}
      </div>
    </div>
  );
};

export default OverviewView;

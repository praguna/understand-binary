import { useState, useEffect } from "react";
import type { KnowledgeGraph } from "./types";
import GraphView from "./GraphView";
import DetailPanel from "./DetailPanel";
import SearchBar from "./SearchBar";
import TourMode from "./TourMode";

export default function App() {
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [highlightedNodes, setHighlightedNodes] = useState<Set<string>>(
    new Set()
  );
  const [tourActive, setTourActive] = useState(false);
  const [tourStep, setTourStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("./knowledge-graph.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: KnowledgeGraph) => setGraph(data))
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="app-error">
        <h1>Understand-Binary</h1>
        <p>Could not load knowledge-graph.json: {error}</p>
        <p>Run `understand-binary &lt;path&gt;` first to generate the graph.</p>
      </div>
    );
  }

  if (!graph) {
    return (
      <div className="app-loading">
        <h1>Loading knowledge graph...</h1>
      </div>
    );
  }

  const selectedNode = selectedNodeId ? graph.nodes[selectedNodeId] : null;

  const handleTourStep = (step: number) => {
    setTourStep(step);
    if (graph.tour[step]) {
      setSelectedNodeId(graph.tour[step]);
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title">
          <span className="app-logo">&gt;_</span> {graph.binary_name}
          <span className="app-meta">
            {graph.format} {graph.architecture} &middot;{" "}
            {Object.keys(graph.nodes).length} functions
          </span>
        </div>
        <SearchBar
          graph={graph}
          onSelect={setSelectedNodeId}
          onHighlight={setHighlightedNodes}
        />
      </header>
      <div className="app-body">
        <GraphView
          graph={graph}
          selectedNodeId={selectedNodeId}
          highlightedNodes={highlightedNodes}
          tourActive={tourActive}
          tourStep={tourStep}
          onSelectNode={setSelectedNodeId}
        />
        <DetailPanel
          node={selectedNode}
          graph={graph}
          onNavigate={setSelectedNodeId}
        />
      </div>
      <TourMode
        graph={graph}
        active={tourActive}
        step={tourStep}
        onToggle={() => {
          setTourActive(!tourActive);
          if (!tourActive && graph.tour.length > 0) {
            handleTourStep(0);
          }
        }}
        onStep={handleTourStep}
      />
    </div>
  );
}

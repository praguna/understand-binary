import { useRef, useEffect } from "react";
import cytoscape, { type Core } from "cytoscape";
import fcose from "cytoscape-fcose";
import type { KnowledgeGraph } from "./types";

cytoscape.use(fcose);

const LAYER_COLORS: Record<string, string> = {
  entry: "#ff6b6b",
  network: "#4ecdc4",
  crypto: "#a855f7",
  io: "#22c55e",
  math: "#f59e0b",
  memory: "#ef4444",
  string: "#06b6d4",
  core: "#6b7280",
  unknown: "#374151",
};

interface Props {
  graph: KnowledgeGraph;
  selectedNodeId: string | null;
  highlightedNodes: Set<string>;
  tourActive: boolean;
  tourStep: number;
  onSelectNode: (id: string) => void;
}

export default function GraphView({
  graph,
  selectedNodeId,
  highlightedNodes,
  tourActive,
  onSelectNode,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  // Build and mount cytoscape
  useEffect(() => {
    if (!containerRef.current) return;

    // Count in-degree for sizing
    const inDegree: Record<string, number> = {};
    for (const edge of graph.edges) {
      if (edge.type === "calls") {
        inDegree[edge.target] = (inDegree[edge.target] || 0) + 1;
      }
    }
    const maxDeg = Math.max(1, ...Object.values(inDegree));

    const nodes = Object.values(graph.nodes).map((n) => ({
      data: {
        id: n.id,
        label: n.inferred_name || n.original_name || n.address,
        layer: n.layer,
        color: LAYER_COLORS[n.layer] || LAYER_COLORS.unknown,
        size: 20 + (((inDegree[n.id] || 0) / maxDeg) * 40),
      },
    }));

    const edges = graph.edges
      .filter((e) => e.type === "calls")
      .map((e, i) => ({
        data: { id: `e${i}`, source: e.source, target: e.target },
      }));

    const cy = cytoscape({
      container: containerRef.current,
      elements: [...nodes, ...edges],
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(color)",
            label: "data(label)",
            width: "data(size)",
            height: "data(size)",
            "font-size": "10px",
            color: "#e5e7eb",
            "text-valign": "bottom",
            "text-margin-y": 5,
            "text-outline-color": "#111827",
            "text-outline-width": 2,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1,
            "line-color": "#374151",
            "target-arrow-color": "#374151",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.4,
          },
        },
        {
          selector: "node.selected",
          style: {
            "border-width": 3,
            "border-color": "#ffffff",
          },
        },
        {
          selector: "node.highlighted",
          style: {
            "border-width": 2,
            "border-color": "#fbbf24",
          },
        },
        {
          selector: "node.tour-active",
          style: {
            "border-width": 3,
            "border-color": "#38bdf8",
          },
        },
        {
          selector: "edge.tour-edge",
          style: {
            "line-color": "#38bdf8",
            "target-arrow-color": "#38bdf8",
            width: 3,
            opacity: 1,
          },
        },
      ],
      layout: {
        name: "fcose",
        animate: false,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: 120,
        nodeRepulsion: 8000,
      } as cytoscape.LayoutOptions,
    });

    cy.on("tap", "node", (evt) => {
      onSelectNode(evt.target.id());
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
    };
    // Only rebuild on graph change
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [graph]);

  // Handle selection changes
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.nodes().removeClass("selected");
    if (selectedNodeId) {
      const node = cy.getElementById(selectedNodeId);
      node.addClass("selected");
      cy.animate({ center: { eles: node }, duration: 300 });
    }
  }, [selectedNodeId]);

  // Handle search highlights
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.nodes().removeClass("highlighted");
    highlightedNodes.forEach((id) => {
      cy.getElementById(id).addClass("highlighted");
    });
  }, [highlightedNodes]);

  // Handle tour highlighting
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.nodes().removeClass("tour-active");
    cy.edges().removeClass("tour-edge");

    if (tourActive && graph.tour.length > 0) {
      graph.tour.forEach((id) => {
        cy.getElementById(id).addClass("tour-active");
      });
      // Highlight tour edges
      for (let i = 0; i < graph.tour.length - 1; i++) {
        const src = graph.tour[i];
        const tgt = graph.tour[i + 1];
        cy.edges(`[source="${src}"][target="${tgt}"]`).addClass("tour-edge");
      }
    }
  }, [tourActive, graph.tour]);

  return <div ref={containerRef} className="graph-view" />;
}

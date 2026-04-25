import { useEffect, useRef } from "react";
import Prism from "prismjs";
import "prismjs/components/prism-c";
import type { BinaryNode, KnowledgeGraph } from "./types";

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
  node: BinaryNode | null;
  graph: KnowledgeGraph;
  onNavigate: (id: string) => void;
}

export default function DetailPanel({ node, graph, onNavigate }: Props) {
  const codeRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (codeRef.current) {
      Prism.highlightElement(codeRef.current);
    }
  }, [node?.decompiled]);

  if (!node) {
    return (
      <div className="detail-panel detail-panel-empty">
        <p>Click a node to inspect</p>
      </div>
    );
  }

  const calls = graph.edges
    .filter((e) => e.source === node.id && e.type === "calls")
    .map((e) => graph.nodes[e.target])
    .filter(Boolean);

  const calledBy = graph.edges
    .filter((e) => e.target === node.id && e.type === "calls")
    .map((e) => graph.nodes[e.source])
    .filter(Boolean);

  return (
    <div className="detail-panel">
      <div className="detail-header">
        <h2>{node.inferred_name || node.original_name}</h2>
        {node.inferred_name && node.inferred_name !== node.original_name && (
          <span className="detail-original">{node.original_name}</span>
        )}
      </div>

      <div className="detail-meta">
        <span
          className="layer-badge"
          style={{ backgroundColor: LAYER_COLORS[node.layer] || "#374151" }}
        >
          {node.layer}
        </span>
        <span className="detail-address">{node.address}</span>
        {node.metadata.complexity != null ? (
          <span className="detail-complexity">
            {String(node.metadata.complexity)}
          </span>
        ) : null}
      </div>

      {node.summary && (
        <div className="detail-section">
          <h3>Summary</h3>
          <p>{node.summary}</p>
        </div>
      )}

      {node.decompiled && (
        <div className="detail-section">
          <h3>Decompiled</h3>
          <pre className="detail-code">
            <code ref={codeRef} className="language-c">
              {node.decompiled}
            </code>
          </pre>
        </div>
      )}

      {calls.length > 0 && (
        <div className="detail-section">
          <h3>Calls ({calls.length})</h3>
          <ul className="detail-ref-list">
            {calls.map((n) => (
              <li key={n.id}>
                <button onClick={() => onNavigate(n.id)}>
                  {n.inferred_name || n.original_name}
                </button>
                <span
                  className="layer-dot"
                  style={{
                    backgroundColor: LAYER_COLORS[n.layer] || "#374151",
                  }}
                />
              </li>
            ))}
          </ul>
        </div>
      )}

      {calledBy.length > 0 && (
        <div className="detail-section">
          <h3>Called by ({calledBy.length})</h3>
          <ul className="detail-ref-list">
            {calledBy.map((n) => (
              <li key={n.id}>
                <button onClick={() => onNavigate(n.id)}>
                  {n.inferred_name || n.original_name}
                </button>
                <span
                  className="layer-dot"
                  style={{
                    backgroundColor: LAYER_COLORS[n.layer] || "#374151",
                  }}
                />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

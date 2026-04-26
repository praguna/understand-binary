import type { KnowledgeGraph } from "./types";

interface Props {
  graph: KnowledgeGraph;
  active: boolean;
  step: number;
  onToggle: () => void;
  onStep: (step: number) => void;
}

export default function TourMode({
  graph,
  active,
  step,
  onToggle,
  onStep,
}: Props) {
  if (graph.tour.length === 0) {
    return null;
  }

  const currentNodeId = graph.tour[step];
  const currentNode = currentNodeId ? graph.nodes[currentNodeId] : null;

  return (
    <div className={`tour-mode ${active ? "tour-active" : ""}`}>
      <button className="tour-toggle" onClick={onToggle}>
        {active ? "Exit Tour" : "Start Tour"}
      </button>

      {active && (
        <div className="tour-content">
          <button
            className="tour-nav"
            disabled={step === 0}
            onClick={() => onStep(step - 1)}
          >
            Prev
          </button>

          <div className="tour-info">
            <span className="tour-step">
              Step {step + 1}/{graph.tour.length}
            </span>
            <span className="tour-name">
              {currentNode?.inferred_name || currentNode?.original_name || ""}
            </span>
          </div>

          <button
            className="tour-nav"
            disabled={step === graph.tour.length - 1}
            onClick={() => onStep(step + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

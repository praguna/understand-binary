"""Agent that builds a guided walkthrough of the binary."""

from __future__ import annotations

import json
from collections import defaultdict

from src.agents.base import Agent
from src.core.graph import GraphFragment, KnowledgeGraph, Edge
from src.core.llm import LLMClient
from src.loaders.base import BinaryContext

MAX_TOUR_STEPS = 20


class TourBuilderAgent(Agent):
    name = "tour-builder"
    description = "Build a guided walkthrough from entry point through the binary"
    depends_on = ["function-namer", "summarizer", "layer-classifier"]

    def analyze(self, context: BinaryContext, graph: KnowledgeGraph, llm: LLMClient) -> GraphFragment:
        entry = self._find_entry(context, graph)
        if not entry:
            return GraphFragment()

        tour_ids = self._select_tour_nodes(entry, context, graph)
        narrative = self._generate_narrative(tour_ids, graph, llm)

        fragment = GraphFragment()
        fragment.tour = tour_ids

        # Add tour_next edges
        for i in range(len(tour_ids) - 1):
            fragment.edges.append(Edge(
                source=tour_ids[i],
                target=tour_ids[i + 1],
                type="tour_next",
                metadata={"step": i + 1, "narrative": narrative.get(tour_ids[i], "")},
            ))

        # Store narrative on the last node too
        if tour_ids:
            last_id = tour_ids[-1]
            fragment.edges.append(Edge(
                source=last_id,
                target=last_id,
                type="tour_next",
                metadata={"step": len(tour_ids), "narrative": narrative.get(last_id, "End of tour.")},
            ))

        return fragment

    def _find_entry(self, context: BinaryContext, graph: KnowledgeGraph) -> str:
        """Find the entry point: prefer known entry names, tiebreak by most reachable nodes."""
        entry_names = {"main", "_main", "entry", "entry0", "_start", "WinMain"}

        adj: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            if edge.type == "calls":
                adj[edge.source].append(edge.target)

        def reachable(nid: str) -> int:
            seen: set[str] = set()
            stack = [nid]
            while stack:
                n = stack.pop()
                if n in seen:
                    continue
                seen.add(n)
                stack.extend(adj[n])
            return len(seen)

        candidates = [f"fn_{fn.address}" for fn in context.functions if fn.name in entry_names]
        if candidates:
            return max(candidates, key=reachable)

        # Fallback: node that reaches the most other nodes
        if graph.nodes:
            return max(graph.nodes, key=reachable)
        return ""

    def _select_tour_nodes(self, entry_id: str, context: BinaryContext, graph: KnowledgeGraph) -> list[str]:
        """BFS from entry, prioritizing high in-degree, layer variety, complexity."""
        # Build in-degree map
        in_degree: dict[str, int] = defaultdict(int)
        for edge in graph.edges:
            if edge.type == "calls":
                in_degree[edge.target] += 1

        # BFS from entry
        visited: set[str] = set()
        queue: list[str] = [entry_id]
        tour: list[str] = []
        seen_layers: set[str] = set()

        while queue and len(tour) < MAX_TOUR_STEPS:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            node = graph.nodes.get(current)
            if not node:
                continue

            tour.append(current)
            seen_layers.add(node.layer)

            # Find callees and sort by priority
            callees: list[str] = []
            for edge in graph.edges:
                if edge.source == current and edge.type == "calls":
                    callees.append(edge.target)

            # Sort: prefer new layers, then high in-degree, then complex
            def callee_score(cid: str) -> tuple[int, int, int]:
                cn = graph.nodes.get(cid)
                if not cn:
                    return (0, 0, 0)
                new_layer = 1 if cn.layer not in seen_layers else 0
                complexity = {"complex": 2, "moderate": 1}.get(cn.metadata.get("complexity", ""), 0)
                return (new_layer, in_degree.get(cid, 0), complexity)

            callees.sort(key=callee_score, reverse=True)
            queue.extend(callees)

        return tour

    def _generate_narrative(self, tour_ids: list[str], graph: KnowledgeGraph, llm: LLMClient) -> dict[str, str]:
        """Generate connecting narrative for tour steps."""
        steps_text = ""
        for i, nid in enumerate(tour_ids, 1):
            node = graph.nodes.get(nid)
            if not node:
                continue
            name = node.inferred_name or node.original_name
            steps_text += f"Step {i}: {name} ({node.layer}) - {node.summary}\n"

        prompt = f"""You are creating a guided tour of a binary program for someone learning reverse engineering.

Here are the functions in tour order:
{steps_text}

For each step, write a 1-2 sentence narrative that:
- Explains what happens at this step
- Connects it to the previous step (how we got here)
- Uses simple language

Respond with JSON:
{{
  "narratives": {{
    "{tour_ids[0] if tour_ids else ''}": "The program starts here at the entry point...",
    ...
  }}
}}"""

        try:
            response = llm.chat([{"role": "user", "content": prompt}], json_mode=True)
            data = json.loads(response)
            return data.get("narratives", {})
        except (json.JSONDecodeError, Exception):
            # Fallback: use summaries as narrative
            narratives = {}
            for nid in tour_ids:
                node = graph.nodes.get(nid)
                if node:
                    narratives[nid] = node.summary or f"Function at {node.address}"
            return narratives

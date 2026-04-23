"""Agent that generates plain-English summaries of functions."""

from __future__ import annotations

import json

from src.agents.base import Agent
from src.core.graph import GraphFragment, KnowledgeGraph, Node
from src.core.llm import LLMClient
from src.loaders.base import BinaryContext


class SummarizerAgent(Agent):
    name = "summarizer"
    description = "Generate plain-English function summaries"
    depends_on = ["function-namer"]

    def analyze(self, context: BinaryContext, graph: KnowledgeGraph, llm: LLMClient) -> GraphFragment:
        fragment = GraphFragment()
        func_nodes = [n for n in graph.nodes.values() if n.type == "function"]
        batch_size = 5

        for i in range(0, len(func_nodes), batch_size):
            batch = func_nodes[i : i + batch_size]
            batch_info = []
            for node in batch:
                decompiled = context.decompile(node.address)
                batch_info.append({
                    "address": node.address,
                    "name": node.inferred_name or node.original_name,
                    "decompiled": decompiled[:2000],
                })

            prompt = self._build_prompt(batch_info)
            try:
                response = llm.chat(
                    [{"role": "user", "content": prompt}],
                    json_mode=True,
                )
                results = json.loads(response)
            except (json.JSONDecodeError, Exception):
                results = {}

            summaries = results.get("summaries", {})
            for node in batch:
                info = summaries.get(node.address, {})
                summary = info.get("summary", "")
                complexity = info.get("complexity", "unknown")

                updated = Node(
                    id=node.id,
                    summary=summary,
                    metadata={"complexity": complexity},
                )
                fragment.nodes.append(updated)

        return fragment

    def _build_prompt(self, batch: list[dict]) -> str:
        functions_text = ""
        for fn in batch:
            functions_text += f"\n--- {fn['name']} at {fn['address']} ---\n"
            functions_text += fn["decompiled"] + "\n"

        return f"""You are explaining a binary program to someone learning reverse engineering. For each function below, provide:
1. A 1-2 sentence plain-English summary of what it does
2. Complexity rating: "simple", "moderate", or "complex"

Functions:
{functions_text}

Respond with JSON:
{{
  "summaries": {{
    "0x401000": {{"summary": "Sets up a TCP socket on the specified port and begins listening for connections.", "complexity": "moderate"}},
    "0x401200": {{"summary": "Copies bytes from source to destination buffer.", "complexity": "simple"}}
  }}
}}"""

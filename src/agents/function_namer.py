"""Agent that infers meaningful function names using an LLM."""

from __future__ import annotations

import json

from src.agents.base import Agent
from src.core.graph import GraphFragment, KnowledgeGraph, Node
from src.core.llm import LLMClient
from src.loaders.base import BinaryContext


class FunctionNamerAgent(Agent):
    name = "function-namer"
    description = "Infer meaningful names for stripped functions"
    depends_on: list[str] = []

    def analyze(self, context: BinaryContext, graph: KnowledgeGraph, llm: LLMClient) -> GraphFragment:
        fragment = GraphFragment()
        functions = context.functions
        batch_size = 10

        for i in range(0, len(functions), batch_size):
            batch = functions[i : i + batch_size]
            batch_info = []
            for fn in batch:
                decompiled = context.decompile(fn.address)
                batch_info.append({
                    "address": fn.address,
                    "current_name": fn.name,
                    "decompiled": decompiled[:2000],  # truncate long functions
                    "size": fn.size,
                })

            prompt = self._build_prompt(batch_info, context.imports, context.strings[:50])
            try:
                response = llm.chat(
                    [{"role": "user", "content": prompt}],
                    json_mode=True,
                )
                results = json.loads(response)
            except (json.JSONDecodeError, Exception):
                results = {}

            names = results.get("functions", {})
            for fn in batch:
                inferred = names.get(fn.address, {})
                name = inferred.get("name", "")
                confidence = inferred.get("confidence", "low")

                node = Node(
                    id=f"fn_{fn.address}",
                    type="function",
                    address=fn.address,
                    original_name=fn.name,
                    inferred_name=name if name else fn.name,
                    metadata={"low_confidence": confidence == "low"} if name else {},
                )
                fragment.nodes.append(node)

        return fragment

    def _build_prompt(self, batch: list[dict], imports: list[str], strings: list[str]) -> str:
        functions_text = ""
        for fn in batch:
            functions_text += f"\n--- Function at {fn['address']} (current name: {fn['current_name']}, size: {fn['size']} bytes) ---\n"
            functions_text += fn["decompiled"] + "\n"

        return f"""You are a reverse engineering expert. Analyze these decompiled functions from a stripped binary and infer meaningful names for each.

Known imports in this binary: {', '.join(imports[:30])}
Sample strings found: {', '.join(strings[:20])}

Functions to analyze:
{functions_text}

For each function, provide:
- A descriptive snake_case name based on what the function does
- Confidence level: "high" if you're fairly sure, "low" if it's a guess

Respond with JSON in this exact format:
{{
  "functions": {{
    "0x401000": {{"name": "initialize_server", "confidence": "high"}},
    "0x401200": {{"name": "parse_input", "confidence": "low"}}
  }}
}}"""

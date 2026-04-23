"""Agent that classifies functions into architectural layers."""

from __future__ import annotations

import json

from src.agents.base import Agent
from src.core.graph import GraphFragment, KnowledgeGraph, Node
from src.core.llm import LLMClient
from src.loaders.base import BinaryContext

# Heuristic mapping: if a function calls these imports, classify it into the layer.
_LAYER_HEURISTICS: dict[str, list[str]] = {
    "network": ["socket", "connect", "bind", "listen", "accept", "send", "recv", "sendto",
                 "recvfrom", "getaddrinfo", "gethostbyname", "select", "poll", "epoll",
                 "WSAStartup", "WSASocket", "htons", "ntohs", "inet_"],
    "crypto": ["SHA", "sha1", "sha256", "MD5", "md5", "AES", "aes_", "EVP_", "HMAC",
               "RSA", "EC_", "SSL_", "TLS", "encrypt", "decrypt", "cipher"],
    "io": ["fopen", "fclose", "fread", "fwrite", "fgets", "fputs", "open", "close",
           "read", "write", "lseek", "stat", "fstat", "mkdir", "rmdir", "unlink",
           "CreateFile", "ReadFile", "WriteFile", "printf", "fprintf", "scanf"],
    "memory": ["malloc", "calloc", "realloc", "free", "mmap", "munmap", "brk",
               "VirtualAlloc", "VirtualFree", "HeapAlloc", "HeapFree", "memcpy",
               "memmove", "memset", "memcmp"],
    "string": ["strlen", "strcpy", "strncpy", "strcat", "strncat", "strcmp", "strncmp",
               "strstr", "strchr", "strrchr", "strtok", "sprintf", "snprintf", "sscanf",
               "atoi", "atof", "strtol", "strtoul", "wcs"],
    "math": ["sin", "cos", "tan", "sqrt", "pow", "exp", "log", "floor", "ceil",
             "fabs", "fmod", "round", "trunc", "cbrt"],
}

_ENTRY_NAMES = {"main", "_start", "entry", "entry0", "WinMain", "DllMain", "_main"}


class LayerClassifierAgent(Agent):
    name = "layer-classifier"
    description = "Classify functions into architectural layers"
    depends_on: list[str] = []

    def analyze(self, context: BinaryContext, graph: KnowledgeGraph, llm: LLMClient) -> GraphFragment:
        fragment = GraphFragment()
        ambiguous: list[Node] = []

        for fn in context.functions:
            node_id = f"fn_{fn.address}"
            layer = self._classify_heuristic(fn.name, fn.address, context)

            if layer:
                fragment.nodes.append(Node(id=node_id, layer=layer))
            else:
                existing = graph.nodes.get(node_id)
                ambiguous.append(existing if existing else Node(id=node_id, address=fn.address, original_name=fn.name))

        # LLM fallback for ambiguous functions
        if ambiguous:
            llm_results = self._classify_with_llm(ambiguous, context, llm)
            fragment.nodes.extend(llm_results)

        return fragment

    def _classify_heuristic(self, name: str, address: str, context: BinaryContext) -> str:
        if name in _ENTRY_NAMES:
            return "entry"

        # Check what this function calls
        callees = context.call_graph.get(address, [])
        callee_names = set()
        for callee_addr in callees:
            for fn in context.functions:
                if fn.address == callee_addr:
                    callee_names.add(fn.name)
                    break

        # Also check imports referenced
        all_refs = callee_names | {name}
        for ref in list(all_refs):
            all_refs.add(ref.lower())

        layer_scores: dict[str, int] = {}
        for layer, keywords in _LAYER_HEURISTICS.items():
            score = sum(1 for kw in keywords if any(kw.lower() in ref for ref in all_refs))
            if score > 0:
                layer_scores[layer] = score

        if layer_scores:
            return max(layer_scores, key=layer_scores.get)
        return ""

    def _classify_with_llm(self, nodes: list[Node], context: BinaryContext, llm: LLMClient) -> list[Node]:
        result_nodes: list[Node] = []
        batch_size = 15

        for i in range(0, len(nodes), batch_size):
            batch = nodes[i : i + batch_size]
            funcs_text = ""
            for node in batch:
                name = node.inferred_name or node.original_name or node.id
                summary = node.summary or ""
                funcs_text += f"  {node.address}: name={name}, summary={summary}\n"

            prompt = f"""Classify these binary functions into architectural layers.
Layers: entry, network, crypto, io, math, memory, string, core, unknown

Functions:
{funcs_text}

Respond with JSON:
{{
  "layers": {{
    "0x401000": "network",
    "0x401200": "core"
  }}
}}"""
            try:
                response = llm.chat([{"role": "user", "content": prompt}], json_mode=True)
                data = json.loads(response)
            except (json.JSONDecodeError, Exception):
                data = {}

            layers = data.get("layers", {})
            for node in batch:
                layer = layers.get(node.address, "unknown")
                result_nodes.append(Node(id=node.id, layer=layer))

        return result_nodes

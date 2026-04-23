"""Knowledge graph data model for Understand-Binary."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class Node:
    id: str
    type: str = "function"  # function, string, data_structure, import, section
    address: str = ""
    original_name: str = ""
    inferred_name: str = ""
    summary: str = ""
    layer: str = "unknown"  # entry, network, crypto, io, math, memory, string, core, unknown
    decompiled: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def update_from(self, other: Node) -> None:
        """Update fields from another node. Only non-empty/non-default fields overwrite."""
        for fld in ["type", "address", "original_name", "inferred_name", "summary", "layer", "decompiled"]:
            value = getattr(other, fld)
            if value and value != "unknown" and value != "function":
                setattr(self, fld, value)
        if other.metadata:
            self.metadata.update(other.metadata)


@dataclass
class Edge:
    source: str
    target: str
    type: str = "calls"  # calls, called_by, reads, writes, references, tour_next
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphFragment:
    """What each agent returns. Merged into the full graph by the orchestrator."""
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    tour: list[str] = field(default_factory=list)


@dataclass
class KnowledgeGraph:
    binary_name: str = ""
    architecture: str = ""
    format: str = ""
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    tour: list[str] = field(default_factory=list)

    def merge(self, fragment: GraphFragment) -> None:
        """Merge a GraphFragment into this graph.

        Non-null fields in fragment nodes overwrite existing node fields.
        Edges are appended. Tour is replaced if fragment provides one.
        """
        for node in fragment.nodes:
            if node.id in self.nodes:
                self.nodes[node.id].update_from(node)
            else:
                self.nodes[node.id] = node
        self.edges.extend(fragment.edges)
        if fragment.tour:
            self.tour = fragment.tour

    def to_dict(self) -> dict[str, Any]:
        return {
            "binary_name": self.binary_name,
            "architecture": self.architecture,
            "format": self.format,
            "nodes": {nid: asdict(node) for nid, node in self.nodes.items()},
            "edges": [asdict(edge) for edge in self.edges],
            "tour": self.tour,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeGraph:
        graph = cls(
            binary_name=data.get("binary_name", ""),
            architecture=data.get("architecture", ""),
            format=data.get("format", ""),
        )
        for nid, ndata in data.get("nodes", {}).items():
            graph.nodes[nid] = Node(**ndata)
        for edata in data.get("edges", []):
            graph.edges.append(Edge(**edata))
        graph.tour = data.get("tour", [])
        return graph

    @classmethod
    def from_json(cls, text: str) -> KnowledgeGraph:
        return cls.from_dict(json.loads(text))

    @classmethod
    def read(cls, path: Path) -> KnowledgeGraph:
        return cls.from_json(path.read_text(encoding="utf-8"))

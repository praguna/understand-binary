"""Abstract base class for analysis agents."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.graph import GraphFragment, KnowledgeGraph
from src.core.llm import LLMClient
from src.loaders.base import BinaryContext


class Agent(ABC):
    """Base class for agents. Drop a subclass in agents/ to add a new analysis pass."""

    name: str = "base"
    description: str = ""
    depends_on: list[str] = []

    @abstractmethod
    def analyze(self, context: BinaryContext, graph: KnowledgeGraph, llm: LLMClient) -> GraphFragment:
        """Analyze the binary and return nodes/edges to merge into the graph."""

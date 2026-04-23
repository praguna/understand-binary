"""Abstract base class for binary loaders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FunctionInfo:
    address: str
    name: str
    size: int = 0


@dataclass
class BinaryContext:
    binary_name: str = ""
    architecture: str = ""
    format: str = ""
    sections: list[dict[str, Any]] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    strings: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    call_graph: dict[str, list[str]] = field(default_factory=dict)

    _loader: Any = field(default=None, repr=False)

    def decompile(self, address: str) -> str:
        """Decompile a function at the given address using the loader."""
        if self._loader is None:
            return ""
        return self._loader.decompile(address)


class BinaryLoader(ABC):
    """Base class for binary loaders. Drop a subclass in loaders/ to add support."""

    name: str = "base"
    supported_formats: list[str] = []

    @abstractmethod
    def load(self, path: str) -> BinaryContext:
        """Load a binary and return its context."""

    @abstractmethod
    def decompile(self, address: str) -> str:
        """Return decompiled pseudo-C for a function at the given address."""

    def supports(self, binary_format: str) -> bool:
        return binary_format.upper() in [f.upper() for f in self.supported_formats]

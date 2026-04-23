"""Auto-discovery of agent and loader plugins."""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path
from typing import TypeVar, Type

T = TypeVar("T")


def _discover(directory: Path, base_class: Type[T]) -> list[T]:
    """Scan a directory for Python modules and return instances of all base_class subclasses."""
    instances: list[T] = []
    if not directory.is_dir():
        return instances

    for py_file in sorted(directory.glob("*.py")):
        if py_file.name.startswith("_") or py_file.name == "base.py":
            continue

        module_name = f"understand_binary_plugin_{py_file.stem}"
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            continue

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, base_class) and obj is not base_class:
                instances.append(obj())

    return instances


def discover_agents(agents_dir: Path | None = None) -> list:
    """Discover all Agent subclasses in the agents directory."""
    from src.agents.base import Agent
    if agents_dir is None:
        agents_dir = Path(__file__).parent.parent / "agents"
    return _discover(agents_dir, Agent)


def discover_loaders(loaders_dir: Path | None = None) -> list:
    """Discover all BinaryLoader subclasses in the loaders directory."""
    from src.loaders.base import BinaryLoader
    if loaders_dir is None:
        loaders_dir = Path(__file__).parent.parent / "loaders"
    return _discover(loaders_dir, BinaryLoader)

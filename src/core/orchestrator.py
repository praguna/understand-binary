"""Orchestrator: runs the analysis pipeline."""

from __future__ import annotations

import json
import subprocess
import sys
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from rich.console import Console

from src.core.graph import KnowledgeGraph, Node, Edge
from src.core.llm import LLMClient
from src.core.plugin import discover_agents, discover_loaders
from src.agents.base import Agent
from src.loaders.base import BinaryContext

console = Console(stderr=True)


@dataclass
class Options:
    output: str = ".understand-binary"
    format: str = "json"
    agent_filter: list[str] = field(default_factory=list)
    llm_provider: str = "openai"
    llm_model: str = ""
    no_viewer: bool = False
    port: int = 3000
    verbose: bool = False


class Orchestrator:
    def __init__(self, options: Options | None = None) -> None:
        self.options = options or Options()

    def run(self, binary_path: str) -> KnowledgeGraph:
        opts = self.options
        log = console.print if opts.verbose else lambda *a, **kw: None

        # 1. Discover plugins
        loaders = discover_loaders()
        agents = discover_agents()
        log(f"[dim]Discovered {len(loaders)} loader(s), {len(agents)} agent(s)[/dim]")

        # 2. Filter agents if requested
        if opts.agent_filter:
            agents = [a for a in agents if a.name in opts.agent_filter]

        # 3. Load binary
        loader = loaders[0] if loaders else None
        if loader is None:
            console.print("[red]No binary loader found. Is rzpipe installed?[/red]")
            sys.exit(1)

        console.print(f"[bold]Loading binary...[/bold] {binary_path}")
        context = loader.load(binary_path)
        console.print(
            f"[green]{context.format} {context.architecture}, "
            f"{len(context.functions)} functions[/green]"
        )

        # 4. Build initial graph from loader data
        graph = KnowledgeGraph(
            binary_name=context.binary_name,
            architecture=context.architecture,
            format=context.format,
        )
        # Populate initial nodes from function list
        for fn in context.functions:
            node_id = f"fn_{fn.address}"
            graph.nodes[node_id] = Node(
                id=node_id,
                type="function",
                address=fn.address,
                original_name=fn.name,
                decompiled=context.decompile(fn.address),
            )
        # Populate call edges
        for caller_addr, callee_addrs in context.call_graph.items():
            for callee_addr in callee_addrs:
                graph.edges.append(Edge(
                    source=f"fn_{caller_addr}",
                    target=f"fn_{callee_addr}",
                    type="calls",
                ))

        # 5. Create LLM client
        llm = LLMClient(provider=opts.llm_provider, model=opts.llm_model)

        # 6. Run agents respecting dependencies
        console.print("[bold]Running agents...[/bold]")
        self._run_agents(agents, context, graph, llm, log)

        # 7. Write output
        output_dir = Path(opts.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        graph_path = output_dir / "knowledge-graph.json"
        graph.write(graph_path)
        console.print(f"\n[green]Graph written to {graph_path}[/green]")

        # 8. Launch viewer
        if not opts.no_viewer and opts.format != "json":
            self._launch_viewer(output_dir, opts.port)

        return graph

    def _run_agents(
        self,
        agents: list[Agent],
        context: BinaryContext,
        graph: KnowledgeGraph,
        llm: LLMClient,
        log: Callable,
    ) -> None:
        """Run agents respecting dependency order, parallelizing where possible."""
        completed: set[str] = set()
        remaining = list(agents)

        while remaining:
            # Find agents whose dependencies are all satisfied
            ready = [a for a in remaining if all(d in completed for d in a.depends_on)]
            if not ready:
                # Circular dependency or missing agent — run everything left
                ready = remaining

            # Run ready agents in parallel
            with ThreadPoolExecutor(max_workers=len(ready)) as executor:
                futures = {executor.submit(a.analyze, context, graph, llm): a for a in ready}
                for future in as_completed(futures):
                    agent = futures[future]
                    try:
                        fragment = future.result()
                        graph.merge(fragment)
                        console.print(f"  [green]\u2713[/green] {agent.name}: {len(fragment.nodes)} nodes, {len(fragment.edges)} edges")
                    except Exception as e:
                        console.print(f"  [red]\u2717[/red] {agent.name}: {e}")

                    completed.add(agent.name)

            remaining = [a for a in remaining if a.name not in completed]

    def _launch_viewer(self, output_dir: Path, port: int) -> None:
        viewer_dir = Path(__file__).parent.parent / "viewer" / "dist"
        if viewer_dir.is_dir():
            console.print(f"\n[bold]Viewer ready at http://localhost:{port}[/bold]")
            webbrowser.open(f"http://localhost:{port}")
        else:
            console.print("[yellow]Viewer not built. Run 'npm run build' in src/viewer/ first.[/yellow]")
            console.print(f"[dim]Graph JSON is at {output_dir / 'knowledge-graph.json'}[/dim]")

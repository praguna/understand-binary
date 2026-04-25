"""CLI entry point for understand-binary."""

from __future__ import annotations

import argparse
import sys
from dotenv import load_dotenv

load_dotenv()

from src.core.orchestrator import Orchestrator, Options


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="understand-binary",
        description="Analyze binary executables and produce interactive knowledge graphs.",
    )
    parser.add_argument("binary", help="Path to the binary to analyze")
    parser.add_argument("--output", "-o", default=".understand-binary", help="Output directory (default: .understand-binary)")
    parser.add_argument("--format", "-f", choices=["json", "html"], default="json", help="Output format")
    parser.add_argument("--agents", default="", help="Comma-separated list of agents to run (default: all)")
    parser.add_argument("--llm-provider", default="gemini", choices=["gemini", "openai", "ollama"], help="LLM provider (default: gemini)")
    parser.add_argument("--llm-model", default="", help="LLM model name (default: provider default)")
    parser.add_argument("--no-viewer", action="store_true", help="Don't launch the viewer")
    parser.add_argument("--port", type=int, default=3000, help="Viewer port (default: 3000)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed progress")

    args = parser.parse_args()

    options = Options(
        output=args.output,
        format=args.format,
        agent_filter=[a.strip() for a in args.agents.split(",") if a.strip()],
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        no_viewer=args.no_viewer,
        port=args.port,
        verbose=args.verbose,
    )

    orchestrator = Orchestrator(options)
    orchestrator.run(args.binary)


if __name__ == "__main__":
    main()

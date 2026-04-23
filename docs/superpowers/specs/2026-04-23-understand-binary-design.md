# Understand-Binary: Design Spec

## Overview

A multi-agent CLI tool that analyzes stripped binary executables and produces an interactive knowledge graph. Agents infer function names, generate summaries, classify architectural layers, and build guided walkthroughs — making binary reverse engineering accessible for education and software understanding.

**Primary use cases:** Educational (learn how compiled programs work) and Software RE (understand closed-source tools).

**Tech stack:** Python backend (agents, orchestrator, rizin integration) + TypeScript/React frontend (Cytoscape.js interactive graph viewer).

**Distribution:** CLI-first (`understand-binary ./binary`), optional Claude Code skill wrapper.

---

## Architecture

### Plugin System

Two plugin types, both auto-discovered by scanning directories for subclasses:

- **Loaders** (`src/loaders/`): Load and decompile binaries. Each loader declares `supported_formats`. The orchestrator picks the matching loader for the input file.
- **Agents** (`src/agents/`): Analyze the binary and contribute nodes/edges to the knowledge graph. Each agent implements `analyze(context) -> GraphFragment`.

Adding a new loader or agent = drop a Python file in the right directory. No config, no registration.

### Pipeline Flow

```
Binary file
  │
  ▼
Plugin Discovery (scan loaders/ and agents/)
  │
  ▼
Loader (rizin_loader for v0.1)
  → BinaryContext: architecture, format, sections, functions, strings, imports, call graph
  │
  ▼
Agent Pipeline:
  ┌─ function_namer ─┐
  │                   ├──→ summarizer ──→ tour_builder
  └─ layer_classifier─┘
  │
  ▼
Graph Merger → KnowledgeGraph
  │
  ▼
Output: .understand-binary/knowledge-graph.json
  │
  ▼
React Viewer at localhost:3000
```

### Project Structure

```
understand-binary/
├── src/
│   ├── core/
│   │   ├── orchestrator.py      # Runs pipeline: discover → load → agents → merge → output
│   │   ├── graph.py             # KnowledgeGraph, GraphFragment, Node, Edge dataclasses
│   │   ├── llm.py               # OpenAI-compatible LLM client (swappable provider)
│   │   └── plugin.py            # Auto-discovery: scans dirs for Agent/Loader subclasses
│   ├── loaders/
│   │   ├── base.py              # Abstract BinaryLoader class
│   │   └── rizin_loader.py      # Default loader: ELF, PE, Mach-O via rizin/rzpipe
│   ├── agents/
│   │   ├── base.py              # Abstract Agent class
│   │   ├── function_namer.py    # LLM infers meaningful function names
│   │   ├── summarizer.py        # LLM generates plain-English summaries
│   │   ├── layer_classifier.py  # Categorizes functions into architectural layers
│   │   └── tour_builder.py      # Builds guided walkthrough from entry point
│   ├── cli/
│   │   └── main.py              # CLI entry point: argparse → orchestrator → viewer
│   └── viewer/                  # React + Cytoscape.js
│       └── src/
│           ├── App.tsx           # Main app shell
│           ├── GraphView.tsx     # Force-directed graph canvas
│           ├── DetailPanel.tsx   # Selected node: decompiled code + summary
│           ├── SearchBar.tsx     # Fuzzy search across names and summaries
│           └── TourMode.tsx      # Step-by-step walkthrough navigation
├── skill/
│   └── understand-binary.md     # Claude Code skill wrapper
├── tests/
├── pyproject.toml
└── README.md
```

---

## Data Model

### Node

| Field | Type | Description |
|---|---|---|
| id | str | `"fn_0x4012a0"` or `"str_0x6030"` |
| type | str | `"function"`, `"string"`, `"data_structure"`, `"import"`, `"section"` |
| address | str | Hex address in binary |
| original_name | str | Name from binary symbols (e.g., `"sub_4012a0"`) |
| inferred_name | str | LLM-inferred name (e.g., `"parse_http_header"`) |
| summary | str | Plain-English description |
| layer | str | `"entry"`, `"network"`, `"crypto"`, `"io"`, `"math"`, `"memory"`, `"string"`, `"core"`, `"unknown"` |
| decompiled | str | Decompiled C from loader |
| metadata | dict | Agent-specific extras (complexity, confidence, flags) |

### Edge

| Field | Type | Description |
|---|---|---|
| source | str | Source node id |
| target | str | Target node id |
| type | str | `"calls"`, `"called_by"`, `"reads"`, `"writes"`, `"references"`, `"tour_next"` |
| metadata | dict | Agent-specific (call count, tour step number) |

### GraphFragment

What each agent returns. Contains a list of nodes and edges to merge into the knowledge graph.

**Merge rules:** When a fragment references an existing node (same `id`), only non-null fields in the fragment overwrite the existing node. Fields set by other agents are preserved. If two agents set the same field on the same node, the later agent in the pipeline wins. Edges are append-only (no deduplication needed since agents produce distinct edge types).

### KnowledgeGraph

Top-level container with `binary_name`, `architecture`, `format`, `nodes` (dict by id), `edges` (list), and `tour` (ordered list of node ids).

Output: `.understand-binary/knowledge-graph.json`

---

## Agent Details (v0.1)

### function_namer
- **Input:** Decompiled C for each function
- **Output:** GraphFragment with `inferred_name` set
- **Strategy:** Batch 10 functions per LLM call. Prompt includes decompiled code, referenced strings, called imports. Returns JSON map of old→new names. Adds `low_confidence` flag when unsure.

### summarizer
- **Input:** Decompiled C + inferred name (depends on function_namer)
- **Output:** GraphFragment with `summary` and complexity metadata
- **Strategy:** Batch 5 functions per LLM call. Target: 1-2 sentence explanation aimed at someone learning how the binary works.

### layer_classifier
- **Input:** Function name + summary + syscalls/imports used
- **Output:** GraphFragment with `layer` set
- **Strategy:** Heuristic first (check which libc/system calls are used — free, no LLM cost). LLM fallback for ambiguous functions only.

### tour_builder
- **Input:** Full knowledge graph (runs last)
- **Output:** GraphFragment with `tour_next` edges and tour ordering
- **Strategy:** Start at entry point, follow call graph breadth-first. Prioritize high in-degree functions, different layers, complex functions. LLM generates connecting narrative. Capped at ~20 steps.

### Execution Order
```
┌─ function_namer ─┐
│                   ├──→ summarizer ──→ tour_builder
└─ layer_classifier─┘
```
function_namer and layer_classifier run in parallel. summarizer depends on function_namer. tour_builder runs last.

---

## Viewer

### Layout
- **GraphView** (left): Cytoscape.js force-directed graph. Nodes colored by layer, sized by in-degree. Click to select, hover for tooltip.
- **DetailPanel** (right): Inferred name, layer badge, summary, syntax-highlighted decompiled C, relationship list (clickable to navigate).
- **SearchBar** (top): Fuzzy search across names and summaries. Type "socket" to highlight all network functions.
- **TourMode** (bottom): Prev/Next navigation, step narrative, auto-centers graph on current node, highlights tour path.

### Serving
CLI writes `knowledge-graph.json`, copies built viewer to `.understand-binary/viewer/`, serves static files via simple HTTP server. No live backend required.

### Export
`--format html` produces a single self-contained HTML file with graph data embedded. Shareable via GitHub issues, email, etc.

---

## CLI Interface

```bash
understand-binary ./sqlite3                              # basic usage
understand-binary ./sqlite3 --output ./report            # custom output dir
understand-binary ./sqlite3 --format html                # self-contained HTML
understand-binary ./sqlite3 --agents namer,layer         # pick agents
understand-binary ./sqlite3 --llm-provider ollama        # local LLM
understand-binary ./sqlite3 --no-viewer                  # JSON only, no browser
understand-binary ./sqlite3 --verbose                    # show agent progress
```

---

## Claude Code Skill

`skill/understand-binary.md` wraps the CLI:
1. Ask user for binary path if not provided
2. Run `understand-binary {path} --format json --verbose`
3. Read knowledge-graph.json, summarize findings
4. Offer to open interactive viewer

---

## v0.1 Scope

| Included | Future |
|---|---|
| rizin loader (ELF, PE, Mach-O) | Ghidra loader, binwalk loader |
| 4 agents: namer, summarizer, layer, tour | vuln-scanner, crypto-detector, struct-recoverer |
| Knowledge graph JSON output | Binary diffing |
| React + Cytoscape.js viewer | Basic block / instruction level zoom (Level 3-4 tours) |
| Fuzzy search | Semantic search |
| Tour mode (Level 1-2: high-level + function) | Tour Level 3-4 (bytecode walkthrough) |
| CLI with LLM provider choice | Collaborative/shared reports |
| Single HTML export | |

### Demo Target
sqlite3 — public domain, single binary, ~242 functions, interesting architecture.

---

## Future Extensibility

### Loader plugins
Community drops files in `loaders/`: ghidra_loader.py (better decompilation), binwalk_loader.py (firmware), dex_loader.py (Android), wasm_loader.py (WebAssembly).

### Agent plugins
Community drops files in `agents/`: crypto_detector.py, vuln_scanner.py, struct_recoverer.py, protocol_reverser.py, malware_classifier.py.

### Tour depth
v0.2+ adds node types `basic_block` and `instruction` with `contains` and `jumps_to` edges. Viewer supports drill-down from function → blocks → annotated assembly. LLM adds plain-English comments to each instruction.

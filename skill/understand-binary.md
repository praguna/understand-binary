---
name: understand-binary
description: Analyze a binary executable and produce an interactive knowledge graph with inferred function names, summaries, layer classification, and guided tour
---

## Usage

Analyze a stripped binary and explore it through an interactive knowledge graph.

### Steps

1. **Get binary path** — if no argument provided, ask: "What binary would you like to analyze?"

2. **Run analysis:**
```bash
understand-binary {path} --format json --verbose
```

3. **Read results** — load `.understand-binary/knowledge-graph.json` and summarize:
   - Binary: name, format, architecture
   - Functions: total count, how many were named by the LLM
   - Layers detected: list each layer and count
   - Tour: number of steps in the guided walkthrough
   - Notable findings: any functions flagged with low_confidence, most-called functions

4. **Offer viewer:**
   > "Want me to open the interactive graph viewer? I can launch it in your browser."

   If yes: `understand-binary {path} --format html`

5. **Answer follow-up questions** — if the user asks about a specific function:
   - Look it up in the knowledge graph JSON by inferred_name, original_name, or address
   - Show its summary, layer, decompiled code, and what it calls / is called by

### Options

- `--llm-provider ollama` — use a local LLM instead of OpenAI
- `--agents namer,layer` — run only specific agents
- `--no-viewer` — skip launching the browser
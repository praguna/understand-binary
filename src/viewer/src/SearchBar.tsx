import { useState, useRef, useMemo } from "react";
import Fuse from "fuse.js";
import type { KnowledgeGraph } from "./types";

interface Props {
  graph: KnowledgeGraph;
  onSelect: (id: string) => void;
  onHighlight: (ids: Set<string>) => void;
}

export default function SearchBar({ graph, onSelect, onHighlight }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const fuse = useMemo(() => {
    const items = Object.values(graph.nodes).map((n) => ({
      id: n.id,
      inferred_name: n.inferred_name,
      original_name: n.original_name,
      summary: n.summary,
      layer: n.layer,
    }));
    return new Fuse(items, {
      keys: ["inferred_name", "original_name", "summary"],
      threshold: 0.4,
    });
  }, [graph]);

  const results = useMemo(() => {
    if (!query.trim()) return [];
    return fuse.search(query, { limit: 10 });
  }, [fuse, query]);

  const handleChange = (value: string) => {
    setQuery(value);
    setOpen(true);
    const ids = new Set(
      fuse.search(value, { limit: 20 }).map((r) => r.item.id)
    );
    onHighlight(ids);
  };

  const handleSelect = (id: string) => {
    onSelect(id);
    setOpen(false);
    onHighlight(new Set());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && results.length > 0) {
      handleSelect(results[0].item.id);
    } else if (e.key === "Escape") {
      setOpen(false);
      onHighlight(new Set());
      inputRef.current?.blur();
    }
  };

  return (
    <div className="search-bar">
      <input
        ref={inputRef}
        type="text"
        placeholder="Search functions..."
        value={query}
        onChange={(e) => handleChange(e.target.value)}
        onFocus={() => query && setOpen(true)}
        onKeyDown={handleKeyDown}
      />
      {open && results.length > 0 && (
        <ul className="search-results">
          {results.map((r) => (
            <li key={r.item.id} onClick={() => handleSelect(r.item.id)}>
              <span className="search-result-name">
                {r.item.inferred_name || r.item.original_name}
              </span>
              <span className="search-result-layer">{r.item.layer}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export interface BinaryNode {
  id: string;
  type: string;
  address: string;
  original_name: string;
  inferred_name: string;
  summary: string;
  layer: string;
  decompiled: string;
  metadata: Record<string, unknown>;
}

export interface BinaryEdge {
  source: string;
  target: string;
  type: string;
  metadata: Record<string, unknown>;
}

export interface KnowledgeGraph {
  binary_name: string;
  architecture: string;
  format: string;
  nodes: Record<string, BinaryNode>;
  edges: BinaryEdge[];
  tour: string[];
}

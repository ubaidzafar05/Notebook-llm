import type { KnowledgeEdge, KnowledgeNode } from "@/lib/api";
import { cn } from "@/lib/utils";

type KnowledgeGraphViewProps = {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  highlightedSourceId: string | null;
  onNodeHover: (nodeId: string | null) => void;
  onNodeSelect: (node: KnowledgeNode) => void;
};

export function KnowledgeGraphView({
  nodes,
  edges,
  highlightedSourceId,
  onNodeHover,
  onNodeSelect,
}: KnowledgeGraphViewProps): JSX.Element {
  if (nodes.length === 0) {
    return (
      <div className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-6 text-sm text-[color:var(--text-muted)]">
        Add sources to see their relationships here.
      </div>
    );
  }
  const limitedNodes = nodes.slice(0, 40);
  const nodeMap = new Map(limitedNodes.map((node) => [node.id, node]));
  const safeEdges = edges.filter((edge) => nodeMap.has(edge.from) && nodeMap.has(edge.to)).slice(0, 60);
  const positions = limitedNodes.map((node) => node.position);
  const minX = Math.min(...positions.map((p) => p.x));
  const maxX = Math.max(...positions.map((p) => p.x));
  const minY = Math.min(...positions.map((p) => p.y));
  const maxY = Math.max(...positions.map((p) => p.y));
  const width = 720;
  const height = 420;

  function projectX(value: number): number {
    if (maxX === minX) return width / 2;
    return ((value - minX) / (maxX - minX)) * (width - 80) + 40;
  }

  function projectY(value: number): number {
    if (maxY === minY) return height / 2;
    return ((value - minY) / (maxY - minY)) * (height - 80) + 40;
  }

  return (
    <div className="rounded-2xl border border-[color:var(--panel-border)] bg-[color:var(--surface-2)] p-4">
      <svg className="h-[420px] w-full" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Knowledge graph">
        <g stroke="rgba(120, 104, 207, 0.25)" strokeWidth="1">
          {safeEdges.map((edge) => {
            const from = nodeMap.get(edge.from);
            const to = nodeMap.get(edge.to);
            if (!from || !to) return null;
            return (
              <line
                key={edge.id}
                x1={projectX(from.position.x)}
                y1={projectY(from.position.y)}
                x2={projectX(to.position.x)}
                y2={projectY(to.position.y)}
                stroke={edge.accent}
                opacity={0.35}
              />
            );
          })}
        </g>
        <g>
          {limitedNodes.map((node) => {
            const isHighlighted = highlightedSourceId ? node.sourceId === highlightedSourceId : false;
            const radius = node.size === "lg" ? 12 : node.size === "md" ? 9 : 7;
            return (
              <g
                key={node.id}
                onMouseEnter={() => onNodeHover(node.id)}
                onMouseLeave={() => onNodeHover(null)}
                onClick={() => onNodeSelect(node)}
                className="cursor-pointer"
              >
                <circle
                  cx={projectX(node.position.x)}
                  cy={projectY(node.position.y)}
                  r={radius}
                  className={cn("transition", isHighlighted ? "opacity-100" : "opacity-80")}
                  fill={node.accent}
                />
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}

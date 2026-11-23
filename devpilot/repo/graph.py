"""Repository dependency and import graph with neighbor expansion."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    id: str = Field(..., description="Unique node identifier, e.g. file path or symbol name")
    node_type: str = Field(default="file", description="'file' or 'symbol'")
    metadata: dict[str, Any] = Field(default_factory=dict)


class RepoDependencyGraph:
    """Directed dependency graph representing file imports and symbol relationships."""

    def __init__(self) -> None:
        self.nodes: dict[str, GraphNode] = {}
        self.adj_out: dict[str, set[str]] = defaultdict(set)
        self.adj_in: dict[str, set[str]] = defaultdict(set)
        self.edge_types: dict[tuple[str, str], str] = {}

    def add_node(
        self, node_id: str, node_type: str = "file", metadata: dict[str, Any] | None = None
    ) -> None:
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(
                id=node_id, node_type=node_type, metadata=metadata or {}
            )

    def add_edge(self, source: str, target: str, relationship: str = "imports") -> None:
        self.add_node(source)
        self.add_node(target)
        self.adj_out[source].add(target)
        self.adj_in[target].add(source)
        self.edge_types[(source, target)] = relationship

    def get_dependencies(self, node_id: str) -> set[str]:
        """Returns direct outbound dependencies of a node."""
        return set(self.adj_out.get(node_id, set()))

    def get_dependents(self, node_id: str) -> set[str]:
        """Returns direct inbound dependents of a node."""
        return set(self.adj_in.get(node_id, set()))

    def expand_neighbors(
        self, seed_nodes: list[str], max_hops: int = 1, max_expansion: int = 10
    ) -> list[str]:
        """Performs BFS graph expansion from seed nodes up to max_hops."""
        visited: set[str] = set(seed_nodes)
        queue: deque[tuple[str, int]] = deque((node, 0) for node in seed_nodes)
        expanded: list[str] = []

        while queue and len(expanded) < max_expansion:
            curr_node, hop = queue.popleft()
            if hop >= max_hops:
                continue

            # Check outbound (imports) and inbound (imported-by)
            neighbors = self.adj_out.get(curr_node, set()) | self.adj_in.get(curr_node, set())
            for neighbor in sorted(neighbors):
                if neighbor not in visited and neighbor in self.nodes:
                    visited.add(neighbor)
                    expanded.append(neighbor)
                    queue.append((neighbor, hop + 1))
                    if len(expanded) >= max_expansion:
                        break

        return expanded

    def compute_pagerank(
        self, damping: float = 0.85, max_iter: int = 50, tol: float = 1e-4
    ) -> dict[str, float]:
        """Computes PageRank centrality scores for all nodes in the graph."""
        n = len(self.nodes)
        if n == 0:
            return {}

        node_list = list(self.nodes.keys())
        ranks = dict.fromkeys(node_list, 1.0 / n)

        for _ in range(max_iter):
            new_ranks = {}
            dangling_sum = sum(ranks[node] for node in node_list if not self.adj_out.get(node))
            dangling_contrib = damping * (dangling_sum / n)

            diff = 0.0
            for node in node_list:
                incoming_sum = 0.0
                for source in self.adj_in.get(node, set()):
                    out_degree = len(self.adj_out.get(source, set()))
                    if out_degree > 0:
                        incoming_sum += ranks[source] / out_degree

                rank = (1.0 - damping) / n + dangling_contrib + (damping * incoming_sum)
                new_ranks[node] = rank
                diff += abs(rank - ranks[node])

            ranks = new_ranks
            if diff < tol:
                break

        return ranks

    def to_dict(self) -> dict[str, Any]:
        """Serializes graph to dictionary for REST API or persistence."""
        nodes_data = [
            {"id": n.id, "type": n.node_type, "meta": n.metadata} for n in self.nodes.values()
        ]
        edges_data = [
            {"source": s, "target": t, "type": self.edge_types.get((s, t), "imports")}
            for s, targets in self.adj_out.items()
            for t in targets
        ]
        return {"nodes": nodes_data, "edges": edges_data}

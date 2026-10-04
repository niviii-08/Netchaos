"""Recovery Engine: given the current operational graph and a failed simulation route,
finds the best alternative route using the chosen strategy.

This class does NOT touch the database or FastAPI request objects — it only works
with plain Python data structures and NetworkX graphs.
"""
from __future__ import annotations

import networkx as nx

from app.schemas.recovery import RecoveryStrategy


class RouteCandidate:
    """A candidate alternative route with computed cost metrics."""

    def __init__(self, path: list[str], latency: float, hop_count: int, bandwidth: float) -> None:
        self.path = path
        self.latency = latency
        self.hop_count = hop_count
        self.bandwidth = bandwidth


class RecoveryEngine:
    """Finds the best alternative route on the operational graph.

    The operational graph already excludes failed nodes and failed links
    (built by the caller from the current DB state).
    """

    def __init__(self, operational_graph: nx.Graph) -> None:
        self.G = operational_graph

    def is_route_valid(self, route: list[str]) -> bool:
        """True if every node and every consecutive edge pair in the route exists on the operational graph."""
        if not route or len(route) < 2:
            return False
        for node in route:
            if node not in self.G:
                return False
        for i in range(len(route) - 1):
            if not self.G.has_edge(route[i], route[i + 1]):
                return False
        return True

    def find_best_route(
        self,
        source: str,
        destination: str,
        strategy: RecoveryStrategy,
        latency_weight: float = 1.0,
        hop_weight: float = 2.0,
        bandwidth_weight: float = 0.5,
    ) -> RouteCandidate | None:
        """Find the best route from source to destination using the given strategy.

        Returns None if no route is reachable.
        """
        if source not in self.G or destination not in self.G:
            return None

        if strategy == RecoveryStrategy.SHORTEST_HOP:
            return self._shortest_hop(source, destination)
        elif strategy == RecoveryStrategy.LOWEST_LATENCY:
            return self._lowest_latency(source, destination)
        elif strategy == RecoveryStrategy.HIGHEST_BANDWIDTH:
            return self._highest_bandwidth(source, destination)
        elif strategy == RecoveryStrategy.COMPOSITE:
            return self._composite(source, destination, latency_weight, hop_weight, bandwidth_weight)
        else:
            return self._shortest_hop(source, destination)

    def _shortest_hop(self, source: str, destination: str) -> RouteCandidate | None:
        """Minimize number of hops (nx.shortest_path with no weight = BFS)."""
        try:
            path = nx.shortest_path(self.G, source, destination)
            return self._make_candidate(path)
        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None

    def _lowest_latency(self, source: str, destination: str) -> RouteCandidate | None:
        """Minimize sum of link latencies."""
        try:
            # Weight by latency; ties broken by node id order (deterministic)
            path = nx.shortest_path(self.G, source, destination, weight="latency")
            return self._make_candidate(path)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def _highest_bandwidth(self, source: str, destination: str) -> RouteCandidate | None:
        """Maximize bottleneck bandwidth — use negative bandwidth as weight."""
        # We enumerate simple paths and pick best; for large graphs limit search
        try:
            all_paths = nx.all_simple_paths(self.G, source, destination, cutoff=20)
            best: RouteCandidate | None = None
            for path in all_paths:
                c = self._make_candidate(path)
                if best is None or c.bandwidth > best.bandwidth or (
                    c.bandwidth == best.bandwidth and path < best.path  # lexicographic tie-break
                ):
                    best = c
            return best
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def _composite(
        self,
        source: str,
        destination: str,
        latency_weight: float,
        hop_weight: float,
        bandwidth_weight: float,
    ) -> RouteCandidate | None:
        """Custom composite cost: latency_weight*latency + hop_weight*hops - bandwidth_weight*bandwidth."""
        try:
            all_paths = nx.all_simple_paths(self.G, source, destination, cutoff=20)
            best: RouteCandidate | None = None
            best_cost = float("inf")
            for path in all_paths:
                c = self._make_candidate(path)
                # Lower bandwidth = higher penalty
                bw_penalty = (1.0 / max(c.bandwidth, 0.001)) * bandwidth_weight * 1000
                cost = latency_weight * c.latency + hop_weight * c.hop_count + bw_penalty
                if best is None or cost < best_cost or (cost == best_cost and path < best.path):
                    best = c
                    best_cost = cost
            return best
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def _make_candidate(self, path: list[str]) -> RouteCandidate:
        latency = 0.0
        bandwidth = float("inf")
        for i in range(len(path) - 1):
            edge_data = self.G[path[i]][path[i + 1]]
            latency += edge_data.get("latency", 0.0)
            bw = edge_data.get("bandwidth", float("inf"))
            bandwidth = min(bandwidth, bw)
        hop_count = len(path) - 1
        if bandwidth == float("inf"):
            bandwidth = 0.0
        return RouteCandidate(path=path, latency=latency, hop_count=hop_count, bandwidth=bandwidth)

    def compute_route_metrics(self, route: list[str]) -> tuple[float, int, float]:
        """Return (total_latency, hop_count, bottleneck_bandwidth) for a route on the operational graph."""
        if not route or len(route) < 2:
            return 0.0, 0, 0.0
        latency = 0.0
        bandwidth = float("inf")
        for i in range(len(route) - 1):
            if not self.G.has_edge(route[i], route[i + 1]):
                return 0.0, 0, 0.0
            edge = self.G[route[i]][route[i + 1]]
            latency += edge.get("latency", 0.0)
            bandwidth = min(bandwidth, edge.get("bandwidth", float("inf")))
        if bandwidth == float("inf"):
            bandwidth = 0.0
        return latency, len(route) - 1, bandwidth

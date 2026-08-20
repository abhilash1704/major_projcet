from .road_node import RoadNode
from .road_edge import RoadEdge

class RoadGraph:
    """
    Conceptual container for Road Network graph data.
    Holds nodes and edges for spatial graph routing operations.
    """
    def __init__(self, metadata=None):
        self.nodes = {}  # node_id -> RoadNode
        self.edges = []  # list of RoadEdge
        self.metadata = metadata or {"status": "initialized", "node_count": 0, "edge_count": 0}

    def add_node(self, node: RoadNode):
        self.nodes[node.node_id] = node
        self.metadata["node_count"] = len(self.nodes)

    def add_edge(self, edge: RoadEdge):
        self.edges.append(edge)
        self.metadata["edge_count"] = len(self.edges)

    def get_node(self, node_id):
        return self.nodes.get(str(node_id))

    def to_dict(self):
        return {
            "metadata": self.metadata,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": {nid: node.to_dict() for nid, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges]
        }

__all__ = ["RoadNode", "RoadEdge", "RoadGraph"]

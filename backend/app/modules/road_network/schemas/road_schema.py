"""
Serialisation / Data Transformation schemas for Road Network entities.
"""

class RoadNodeSchema:
    @staticmethod
    def dump(node):
        if not node:
            return None
        if hasattr(node, "to_dict"):
            return node.to_dict()
        return dict(node)

class RoadEdgeSchema:
    @staticmethod
    def dump(edge):
        if not edge:
            return None
        if hasattr(edge, "to_dict"):
            return edge.to_dict()
        return dict(edge)

class RoadNetworkHealthSchema:
    @staticmethod
    def dump(status="ok", module="road-network", extra=None):
        data = {
            "status": status,
            "module": module
        }
        if extra:
            data.update(extra)
        return data

import networkx as nx

# Create a grid graph
G = nx.grid_2d_graph(5, 5, create_using=nx.MultiDiGraph)
for u, v, data in G.edges(data=True):
    data['weight'] = 1.0

# Try proxying the graph to count calls
class GraphProxy:
    def __init__(self, g):
        self._g = g
        self.explored = set()

    def __getattr__(self, name):
        attr = getattr(self._g, name)
        if name in ('adj', '_adj', 'succ', '_succ'):
            # Let's wrap adj/succ so that lookup logs the node
            class AdjProxy:
                def __init__(self, adj, explored):
                    self._adj = adj
                    self._explored = explored
                def __getitem__(self, node):
                    self._explored.add(node)
                    return self._adj[node]
                def __contains__(self, node):
                    return node in self._adj
                def __len__(self):
                    return len(self._adj)
                def __iter__(self):
                    return iter(self._adj)
            return AdjProxy(attr, self.explored)
        return attr

    def __getitem__(self, node):
        self.explored.add(node)
        return self._g[node]

    def __len__(self):
        return len(self._g)

    def __contains__(self, node):
        return node in self._g

    def __iter__(self):
        return iter(self._g)

gp = GraphProxy(G)
path = nx.dijkstra_path(gp, (0, 0), (4, 4))
print("Dijkstra Path:", path)
print("Dijkstra Explored Count:", len(gp.explored))

gp_astar = GraphProxy(G)
heuristic_fn = lambda u, v: abs(u[0] - v[0]) + abs(u[1] - v[1])
path_astar = nx.astar_path(gp_astar, (0, 0), (4, 4), heuristic=heuristic_fn)
print("Astar Path:", path_astar)
print("Astar Explored Count:", len(gp_astar.explored))

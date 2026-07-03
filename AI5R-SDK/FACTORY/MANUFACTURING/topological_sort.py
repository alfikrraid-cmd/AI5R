"""
FM-104.4 Topological Sort
"""

from collections import deque


class TopologicalSorter:

    def sort(self, graph):

        indegree = {node: 0 for node in graph}

        for node, deps in graph.items():
            for dep in deps:
                indegree[node] += 1

        queue = deque(
            sorted(node for node, degree in indegree.items() if degree == 0)
        )

        result = []

        while queue:

            node = queue.popleft()
            result.append(node)

            for target, deps in graph.items():

                if node in deps:
                    indegree[target] -= 1

                    if indegree[target] == 0:
                        queue.append(target)

        if len(result) != len(graph):
            raise RuntimeError(
                "Manufacturing dependency cycle detected."
            )

        return result

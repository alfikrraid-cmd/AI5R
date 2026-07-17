"""
MFG-005C-4
Manufacturing Scheduler

Determines which manufacturing nodes are ready to run next, given an
execution graph and the set of already-completed node ids.

This component is stateless. It delegates directly to the execution
graph's own ready_nodes(completed) method.
"""

from __future__ import annotations

from typing import Any


class ManufacturingScheduler:
    """
    Scheduler determining ready nodes from an execution graph.
    """

    def next_ready(self, execution_graph: Any, completed: set) -> list:
        """
        Return the nodes in execution_graph that are ready to run,
        given the set of already-completed node ids.

        Args:
            execution_graph:
                Graph implementing ready_nodes(completed).
            completed:
                Set of node ids already completed.

        Returns:
            List of ready nodes, as returned by
            execution_graph.ready_nodes(completed).
        """
        if execution_graph is None:
            return []

        return execution_graph.ready_nodes(completed)

"""
MFG-005C-3
Manufacturing Dispatcher

Dispatches ready manufacturing nodes returned by the Manufacturing
Scheduler.

This component is deterministic and stateless. It does not execute any
manufacturing logic; it only produces an ordered dispatch result for
each ready node.
"""

from __future__ import annotations

from typing import Any


class ManufacturingDispatcher:
    """
    Dispatcher for Manufacturing Scheduler output.
    """

    def dispatch(self, ready_nodes: list) -> list[dict[str, Any]]:
        """
        Dispatch ready nodes in deterministic order.

        Args:
            ready_nodes:
                Nodes returned by ManufacturingScheduler.next_ready().
                Each node must expose a node_id attribute.

        Returns:
            List of dispatch results, one per node, ordered
            deterministically by node_id.
        """
        if not ready_nodes:
            return []

        ordered_nodes = sorted(ready_nodes, key=lambda node: node.node_id)

        return [
            {
                "node_id": node.node_id,
                "node": node,
                "status": "dispatched",
            }
            for node in ordered_nodes
        ]

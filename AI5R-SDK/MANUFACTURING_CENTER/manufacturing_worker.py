"""
MFG-005C-6
Manufacturing Worker

Executes a single manufacturing node handed off by the Manufacturing
Runtime/Dispatcher.

This component does not execute any business logic. It simulates
execution by returning a deterministic SUCCESS result for any
well-formed node.
"""

from __future__ import annotations

from typing import Any


class ManufacturingWorker:
    """
    Worker executing a single manufacturing node.
    """

    def execute(self, node: Any) -> dict[str, Any]:
        """
        Execute a single node and return a deterministic result.

        Args:
            node:
                Node exposing a non-empty string node_id attribute.

        Returns:
            Execution result dict with node_id, node, status, and
            execution metadata.

        Raises:
            ValueError: If node is None or does not expose a valid
                node_id.
        """
        if node is None:
            raise ValueError("node is required")

        node_id = getattr(node, "node_id", None)

        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("node must expose a non-empty string node_id")

        return {
            "node_id": node_id,
            "node": node,
            "status": "SUCCESS",
            "metadata": {
                "simulated": True,
                "engine": "manufacturing_worker",
            },
        }

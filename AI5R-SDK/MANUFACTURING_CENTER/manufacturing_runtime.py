"""
MFG-005C-5
Manufacturing Runtime

Drives execution to completion by repeatedly asking the Manufacturing
Scheduler for ready nodes and handing them to the Manufacturing
Dispatcher.

This component does not execute any business logic. Dispatched nodes
are simulated as completed immediately, which is enough to unblock
their dependents on the next iteration.
"""

from __future__ import annotations

from typing import Any

from .manufacturing_dispatcher import ManufacturingDispatcher
from .manufacturing_scheduler import ManufacturingScheduler
from .manufacturing_worker import ManufacturingWorker


class ManufacturingRuntime:
    """
    Runtime driving the Scheduler/Dispatcher loop to completion.
    """

    def __init__(
        self,
        scheduler: ManufacturingScheduler | None = None,
        dispatcher: ManufacturingDispatcher | None = None,
        worker: ManufacturingWorker | None = None,
    ) -> None:
        self.scheduler = scheduler or ManufacturingScheduler()
        self.dispatcher = dispatcher or ManufacturingDispatcher()
        self.worker = worker or ManufacturingWorker()

    def run(self, execution_graph: Any) -> list[dict[str, Any]]:
        """
        Execute all nodes in the graph in deterministic order.

        Args:
            execution_graph:
                Graph implementing all_node_ids() and ready_nodes(completed).

        Returns:
            List of dispatch results in the order they were dispatched.
        """
        if execution_graph is None:
            return []

        completed: set = set()
        all_node_ids = execution_graph.all_node_ids()
        dispatch_log: list[dict[str, Any]] = []

        while completed != all_node_ids:
            ready = self.scheduler.next_ready(execution_graph, completed)

            if not ready:
                break

            dispatched = self.dispatcher.dispatch(ready)

            for entry in dispatched:
                completed.add(entry["node_id"])

            dispatch_log.extend(dispatched)

        return dispatch_log

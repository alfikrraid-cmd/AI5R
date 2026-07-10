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
from .manufacturing_execution_result import ManufacturingExecutionResult
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

    def execute(self, execution_graph: Any) -> ManufacturingExecutionResult:
        """
        Execute all nodes in the graph through the Manufacturing Worker,
        stopping early on the first failure.

        Args:
            execution_graph:
                Graph implementing all_node_ids() and ready_nodes(completed).

        Returns:
            ManufacturingExecutionResult describing the outcome.
        """
        if execution_graph is None:
            return ManufacturingExecutionResult(status="COMPLETED")

        completed: set = set()
        all_node_ids = execution_graph.all_node_ids()
        completed_nodes: list[str] = []
        failed_nodes: list[str] = []
        execution_order: list[str] = []

        while completed != all_node_ids:
            ready = self.scheduler.next_ready(execution_graph, completed)

            if not ready:
                break

            dispatched = self.dispatcher.dispatch(ready)

            failure_encountered = False

            for entry in dispatched:
                worker_result = self.worker.execute(entry["node"])
                node_id = worker_result["node_id"]

                execution_order.append(node_id)

                if worker_result["status"] == "SUCCESS":
                    completed.add(node_id)
                    completed_nodes.append(node_id)
                else:
                    failed_nodes.append(node_id)
                    failure_encountered = True
                    break

            if failure_encountered:
                break

        if failed_nodes:
            status = "FAILED"
        elif completed == all_node_ids:
            status = "COMPLETED"
        else:
            status = "PARTIAL"

        return ManufacturingExecutionResult(
            status=status,
            completed_nodes=tuple(completed_nodes),
            failed_nodes=tuple(failed_nodes),
            execution_order=tuple(execution_order),
        )

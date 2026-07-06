from .task import EmployeeTask
from .execution_result import ExecutionResult


class EmployeeExecutionEngine:
    def execute(self, employee, task):
        if isinstance(task, str):
            task = EmployeeTask(title=task)

        output = {
            "summary": f"{employee.employee_name} executed task: {task.title}",
            "capabilities_used": list(getattr(employee, "capabilities", [])),
        }

        observation = {
            "task_received": task.title,
            "employee_status": getattr(employee, "status", "UNKNOWN"),
        }

        learning = {
            "lesson": "Task execution completed through employee execution engine",
        }

        return ExecutionResult(
            employee_id=employee.employee_id,
            employee_name=employee.employee_name,
            task_id=task.task_id,
            task_title=task.title,
            status="EXECUTED",
            output=output,
            observation=observation,
            learning=learning,
        )

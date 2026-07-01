"""
AI5R CRUD Generator
BC-23.5
"""

CRUD_OPERATIONS = [
    "list",
    "detail",
    "create",
    "update",
    "delete"
]


def generate_crud(module_name, workflow_generator):
    workflows = []

    for operation in CRUD_OPERATIONS:
        workflow = workflow_generator(module_name, operation)
        workflows.append(workflow)

    return workflows

def validate_workflow(workflow):
    required_keys = ["name", "nodes", "connections"]

    for key in required_keys:
        if key not in workflow:
            raise ValueError(f"Missing required workflow key: {key}")

    if not isinstance(workflow["nodes"], list):
        raise ValueError("workflow.nodes must be a list")

    if not isinstance(workflow["connections"], dict):
        raise ValueError("workflow.connections must be an object")

    return True

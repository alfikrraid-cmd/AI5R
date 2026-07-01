from workflow_generator import generate_workflow
from VALIDATOR.validator import validate
from CRUD.generator import generate_crud


class Compiler:

    def build(self, module_name, workflow_type=None, spec_path=None):
        print("Loading compiler...")

        if spec_path:
            validate(spec_path)

        if workflow_type == "crud":
            workflows = generate_crud(module_name, generate_workflow)
            print(f"Generated {len(workflows)} workflows")
            return workflows

        workflow = generate_workflow(module_name, workflow_type)
        print(f"Workflow : {workflow['name']}")
        print("Compiler SUCCESS")
        return workflow


if __name__ == "__main__":
    compiler = Compiler()
    compiler.build("pump", "crud")

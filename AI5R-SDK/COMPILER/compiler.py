from workflow_generator import generate_workflow
from VALIDATOR.validator import validate


class Compiler:

    def build(self, module_name: str, workflow_type: str, spec_path: str = None):
        print("Loading compiler...")

        if spec_path:
            validate(spec_path)

        workflow = generate_workflow(module_name, workflow_type)

        print(f"Workflow : {workflow['name']}")
        print("Compiler SUCCESS")

        return workflow


if __name__ == "__main__":
    compiler = Compiler()
    compiler.build("pump", "detail")

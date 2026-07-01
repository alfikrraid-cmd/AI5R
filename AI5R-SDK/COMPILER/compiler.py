#!/usr/bin/env python3

from workflow_generator import generate_workflow


class Compiler:

    def build(self, module_name: str, workflow_type: str):
        print("Loading compiler...")

        workflow = generate_workflow(module_name, workflow_type)

        print(f"Workflow : {workflow['name']}")
        print("Compiler SUCCESS")

        return workflow


if __name__ == "__main__":
    compiler = Compiler()
    compiler.build("pump", "detail")
